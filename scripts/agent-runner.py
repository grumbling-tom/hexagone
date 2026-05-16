#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "PyJWT>=2.8,<3",
#     "cryptography>=42",
# ]
# ///
"""Pull GitHub issues labelled `agent-plan` and comment a plan on each.

Usage:
    uv run scripts/agent-runner.py                # process all queued issues
    uv run scripts/agent-runner.py --dry-run      # show what would happen
    uv run scripts/agent-runner.py --limit 1      # process at most 1 issue
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import jwt  # PyJWT

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APP_ID = "3734033"
INSTALLATION_ID = "132848302"
PRIVATE_KEY_PATH = Path.home() / ".config" / "hexagone-agent" / "private-key.pem"

LABEL_PLAN = "agent-plan"
LABEL_WORKING = "agent-working"
LABEL_NEEDS_INPUT = "agent-needs-input"
LABEL_DONE = "agent-done"

REPO_OWNER = "grumbling-tom"
REPO_NAME = "hexagone"
REPO = f"{REPO_OWNER}/{REPO_NAME}"

log = logging.getLogger("agent-runner")

# ---------------------------------------------------------------------------
# GitHub App auth
# ---------------------------------------------------------------------------


def mint_installation_token() -> str:
    """Create a short-lived installation token via GitHub App JWT."""
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": APP_ID}
    private_key = PRIVATE_KEY_PATH.read_bytes()
    encoded = jwt.encode(payload, private_key, algorithm="RS256")

    result = subprocess.run(
        [
            "gh", "api",
            f"/app/installations/{INSTALLATION_ID}/access_tokens",
            "--method", "POST",
            "-H", f"Authorization: Bearer {encoded}",
            "--jq", ".token",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------


def gh_api(
    endpoint: str,
    *,
    method: str = "GET",
    token: str,
    body: dict | None = None,
) -> str:
    """Call the GitHub REST API authenticated as the app installation."""
    cmd: list[str] = [
        "gh", "api", endpoint,
        "--method", method,
        "-H", f"Authorization: Bearer {token}",
    ]
    input_data = None
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "--input", "-"]
        input_data = json.dumps(body)

    result = subprocess.run(cmd, capture_output=True, text=True, input=input_data)
    if result.returncode != 0:
        log.error("gh api %s %s failed: %s", method, endpoint, result.stderr)
    return result.stdout.strip()


def fetch_plan_issues(token: str) -> list[dict]:
    """Fetch open issues labelled agent-plan, excluding agent-needs-input."""
    raw = gh_api(
        f"/repos/{REPO}/issues?labels={LABEL_PLAN}&state=open&per_page=10",
        token=token,
    )
    if not raw:
        return []
    issues = json.loads(raw)
    return [
        i for i in issues
        if "pull_request" not in i
        and not any(lab["name"] == LABEL_NEEDS_INPUT for lab in i.get("labels", []))
    ]


def fetch_issue_comments(issue_number: int, *, token: str) -> list[dict]:
    """Fetch all comments on an issue."""
    raw = gh_api(
        f"/repos/{REPO}/issues/{issue_number}/comments?per_page=100",
        token=token,
    )
    if not raw:
        return []
    return json.loads(raw)


def add_label(issue_number: int, label: str, *, token: str) -> None:
    gh_api(
        f"/repos/{REPO}/issues/{issue_number}/labels",
        method="POST",
        token=token,
        body={"labels": [label]},
    )


def remove_label(issue_number: int, label: str, *, token: str) -> None:
    gh_api(
        f"/repos/{REPO}/issues/{issue_number}/labels/{label}",
        method="DELETE",
        token=token,
    )


def comment_on_issue(issue_number: int, body: str, *, token: str) -> None:
    gh_api(
        f"/repos/{REPO}/issues/{issue_number}/comments",
        method="POST",
        token=token,
        body={"body": body},
    )


# ---------------------------------------------------------------------------
# Thread assembly
# ---------------------------------------------------------------------------


def build_issue_thread(issue: dict, comments: list[dict]) -> str:
    """Assemble the full issue thread as context for Claude."""
    parts = [issue.get("body") or "(no description)"]
    for c in comments:
        author = c.get("user", {}).get("login", "unknown")
        parts.append(f"**@{author}** commented:\n\n{c['body']}")
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Claude orchestration
# ---------------------------------------------------------------------------

PLAN_PROMPT = """\
You are an autonomous agent working on the repository `{repo}`.

Your task is to produce a **detailed implementation plan** for the following \
GitHub issue. Do NOT write any code or make any file changes.

## Issue #{number}: {title}

{thread}

## Instructions

1. Thoroughly explore the codebase. Read the files that are relevant to this \
issue — don't just skim directory listings. Understand the existing patterns, \
conventions, and architecture before planning.
2. If prior comments contain human answers to earlier questions, incorporate them.
3. Produce a **detailed, actionable** plan as markdown with these sections:

### Goal
One-sentence summary of what the issue asks for.

### Approach
Step-by-step description of the implementation. Be specific — name the \
functions, components, routes, or patterns you'd use. Reference existing code \
that should be followed as a pattern.

### Files to change
For EACH file, describe:
- The file path
- What specifically to add, modify, or remove
- Key implementation details (function signatures, component props, CSS \
classes, etc.)

For new files, describe their purpose and rough structure.

### Open questions
Anything unclear that needs human input before implementation can begin. \
Omit this section entirely if you have no questions.

4. Output ONLY the plan markdown — nothing else. Do not create branches, \
commits, or PRs.
5. Be thorough. A good plan should be detailed enough that another developer \
(or agent) could implement it without needing to re-explore the codebase. \
Vague summaries like "update the file" or "add the component" are not enough — \
say exactly what to add and how.

IMPORTANT: If you have open questions that would significantly affect the plan, \
you MUST include the "Open questions" section. If the plan is clear and \
actionable without further input, omit it.
"""

OPEN_QUESTIONS_MARKER = "## Open questions"


def run_claude_plan(issue: dict, thread: str) -> str | None:
    """Run Claude in print mode to generate a plan."""
    prompt = PLAN_PROMPT.format(
        repo=REPO,
        number=issue["number"],
        title=issue["title"],
        thread=thread,
    )
    log.info("Running Claude for plan on issue #%d...", issue["number"])
    result = subprocess.run(
        [
            "claude",
            "--print",
            "--model", "sonnet",
            "--permission-mode", "plan",
            prompt,
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "GH_TOKEN": ""},  # no GH access needed for plans
        timeout=1800,  # 30 minutes
    )
    if result.returncode != 0:
        log.error("Claude plan failed (exit %d): %s", result.returncode, result.stderr)
        return None
    return result.stdout.strip()


def has_open_questions(plan: str) -> bool:
    """Check if the plan contains an Open Questions section with content."""
    lower = plan.lower()
    idx = lower.find("## open questions")
    if idx == -1:
        return False
    after = plan[idx + len("## open questions"):].strip()
    # Check there's actual content (not just the heading)
    return len(after) > 0 and after != "None" and after != "N/A"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def process_issue(issue: dict, *, token: str, dry_run: bool) -> None:
    number = issue["number"]
    title = issue["title"]
    log.info("Processing issue #%d: %s", number, title)

    if dry_run:
        log.info("  (dry-run) Would fetch comments, run Claude, and post plan")
        return

    # Mark as in-progress
    add_label(number, LABEL_WORKING, token=token)
    remove_label(number, LABEL_PLAN, token=token)
    comment_on_issue(number, "Picking up this issue to generate a plan.", token=token)

    try:
        comments = fetch_issue_comments(number, token=token)
        thread = build_issue_thread(issue, comments)
        plan = run_claude_plan(issue, thread)

        if plan:
            if has_open_questions(plan):
                comment_on_issue(
                    number,
                    f"## Agent Plan\n\n{plan}\n\n---\n"
                    f"@{REPO_OWNER} — I have some open questions before this plan "
                    f"is actionable. Please respond and re-label `{LABEL_PLAN}` "
                    f"when ready for another pass.",
                    token=token,
                )
                remove_label(number, LABEL_WORKING, token=token)
                add_label(number, LABEL_NEEDS_INPUT, token=token)
            else:
                comment_on_issue(
                    number,
                    f"## Agent Plan\n\n{plan}\n\n---\n"
                    f"@{REPO_OWNER} — plan ready for review.",
                    token=token,
                )
                remove_label(number, LABEL_WORKING, token=token)
                add_label(number, LABEL_DONE, token=token)
        else:
            comment_on_issue(
                number,
                f"@{REPO_OWNER} — failed to generate a plan. "
                f"Check the agent runner logs for details.",
                token=token,
            )
            remove_label(number, LABEL_WORKING, token=token)
            add_label(number, LABEL_DONE, token=token)

    except subprocess.TimeoutExpired:
        log.error("Claude timed out on issue #%d", number)
        comment_on_issue(
            number,
            f"@{REPO_OWNER} — agent timed out working on this issue.",
            token=token,
        )
        remove_label(number, LABEL_WORKING, token=token)
        add_label(number, LABEL_DONE, token=token)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview without running Claude or modifying issues",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Max issues to process (0 = all)",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if not PRIVATE_KEY_PATH.exists():
        log.error("Private key not found at %s", PRIVATE_KEY_PATH)
        sys.exit(1)

    log.info("Minting installation token...")
    token = mint_installation_token()
    log.info("Token minted.")

    log.info("Fetching issues labelled '%s'...", LABEL_PLAN)
    issues = fetch_plan_issues(token)

    if not issues:
        log.info("No issues queued. Nothing to do.")
        return

    if args.limit > 0:
        issues = issues[: args.limit]

    log.info("Found %d issue(s):", len(issues))
    for issue in issues:
        log.info("  #%d: %s", issue["number"], issue["title"])

    for issue in issues:
        process_issue(issue, token=token, dry_run=args.dry_run)

        # Re-mint token between issues (they expire after 1 hour)
        if issue is not issues[-1]:
            log.info("Re-minting token...")
            token = mint_installation_token()

    log.info("All done.")


if __name__ == "__main__":
    main()

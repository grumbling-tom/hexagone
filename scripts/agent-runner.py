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
# Claude orchestration
# ---------------------------------------------------------------------------

PLAN_PROMPT = """\
You are an autonomous planning agent for the repository `{repo}`.

## Your task

Read GitHub issue #{number} and produce a detailed implementation plan. Post \
the plan as a comment on the issue when done.

## Issue #{number}: {title}

The issue and its full comment history are on GitHub. Read them with:

    gh issue view {number} --repo {repo} --comments

## Workflow

1. Read the issue and all its comments to understand what's being asked.
2. Thoroughly explore the codebase. Read the files relevant to this issue — \
don't just skim directory listings. Understand existing patterns, conventions, \
and architecture before planning.
3. If prior comments on the issue contain human answers to earlier agent \
questions, incorporate those answers into your plan.
4. Write a detailed, actionable implementation plan. A good plan should be \
detailed enough that another developer (or agent) could implement it without \
needing to re-explore the codebase.
5. Post the plan as a comment on issue #{number} using:

    gh issue comment {number} --repo {repo} --body-file <file>

   Write the plan to a temporary file first, then use --body-file to post it. \
This avoids shell escaping issues with --body.

## Plan format

Use this markdown structure:

### Goal
One-sentence summary.

### Approach
Step-by-step description of the implementation. Be specific — name the \
functions, components, routes, or patterns you'd use. Include code snippets \
where they clarify the approach. Reference existing code that should be \
followed as a pattern.

### Files to change
For EACH file, describe:
- The file path
- What specifically to add, modify, or remove
- Key implementation details (function signatures, component props, CSS \
classes, etc.)
For new files, describe their purpose and structure.

### Open questions
Anything unclear that needs human input before implementation can begin. \
Omit this section entirely if you have no questions.

## Rules

- Do NOT create branches, commits, PRs, or modify any code files.
- Do NOT write vague summaries like "update the file" — say exactly what to \
add and how.
- After posting the plan comment, output a single line: either \
RESULT:PLAN_POSTED or RESULT:NEEDS_INPUT (if your plan has open questions).
"""


def run_claude_plan(issue: dict, *, token: str) -> str | None:
    """Run Claude as a full agent to explore the codebase and post a plan."""
    prompt = PLAN_PROMPT.format(
        repo=REPO,
        number=issue["number"],
        title=issue["title"],
    )
    log.info("Running Claude agent for plan on issue #%d...", issue["number"])
    result = subprocess.run(
        [
            "claude",
            "--print",
            "--model", "sonnet",
            "--permission-mode", "plan",
            "--allowedTools",
            "Bash(gh issue comment *)",
            "Bash(gh issue view *)",
            "Bash(gh api *)",
        ],
        capture_output=True,
        text=True,
        input=prompt,
        env={**os.environ, "GH_TOKEN": token},
        timeout=1800,  # 30 minutes
    )
    if result.returncode != 0:
        log.error("Claude plan failed (exit %d): %s", result.returncode, result.stderr)
        return None
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def process_issue(issue: dict, *, token: str, dry_run: bool) -> None:
    number = issue["number"]
    title = issue["title"]
    log.info("Processing issue #%d: %s", number, title)

    if dry_run:
        log.info("  (dry-run) Would launch Claude agent to plan and comment")
        return

    # Mark as in-progress
    add_label(number, LABEL_WORKING, token=token)
    remove_label(number, LABEL_PLAN, token=token)
    comment_on_issue(number, "Picking up this issue to generate a plan.", token=token)

    try:
        output = run_claude_plan(issue, token=token)

        if output and "RESULT:NEEDS_INPUT" in output:
            log.info("Issue #%d: agent has open questions", number)
            remove_label(number, LABEL_WORKING, token=token)
            add_label(number, LABEL_NEEDS_INPUT, token=token)
        elif output and "RESULT:PLAN_POSTED" in output:
            log.info("Issue #%d: plan posted successfully", number)
            remove_label(number, LABEL_WORKING, token=token)
            add_label(number, LABEL_DONE, token=token)
        else:
            log.warning("Issue #%d: unexpected output from Claude", number)
            comment_on_issue(
                number,
                f"@{REPO_OWNER} — agent finished but result was unclear. "
                f"Check the issue for a plan comment, or check runner logs.",
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

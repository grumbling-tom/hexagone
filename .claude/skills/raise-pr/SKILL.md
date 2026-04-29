---
name: raise-pr
description: Open a GitHub pull request with a title and body that match this project's established style (One-liner / Context / Technical Decisions / Testing). Use this whenever the user asks to raise, open, ship, or put up a PR — even if they don't mention the skill explicitly. Announce that you're invoking this skill before proceeding. Defaults to draft PRs.
user-invocable: true
allowed-tools: Bash(git status:*) Bash(git branch:*) Bash(git log:*) Bash(git diff:*) Bash(git rev-parse:*) Bash(gh pr list:*) Bash(gh pr create:*) Bash(gh pr view:*) Read Grep Glob
argument-hint: "[optional notes to include]"
---

You are raising a pull request in this project. Before you start, tell the user you're invoking the `raise-pr` skill so they know this flow is running.

## Principles

- **Match the house style, don't invent one.** This project has a distinct PR voice. Read recent merged PRs to absorb it — first person, casual, honest about trade-offs, bullets over prose, and no `feat:` / `fix:` title prefixes.
- **Explain the *why*, not the *what*.** The diff shows what changed. The PR body should explain the motivation, the alternatives considered, and the trade-offs taken. If you find yourself paraphrasing the diff, cut it.
- **Draft with the user, not for them.** Show the draft before creating the PR and let them edit. The user cares about tone and framing — don't ship without their eyes on it.

## Workflow

### 1. Gather context

Run these in parallel:

- `git status` — any uncommitted changes?
- `git branch --show-current` — current branch
- `git log main..HEAD --oneline` — all commits on this branch
- `git diff main...HEAD` — full diff against main (use `...` not `..`)
- `git rev-parse --abbrev-ref --symbolic-full-name @{u}` (or similar) — does the branch have an upstream?
- `gh pr list --state merged --limit 3 --json title,body` — recent merged PRs as a style reference

If there are uncommitted changes, stop and ask the user whether to commit them first or leave them out.

If the branch has no upstream, stop and ask the user to push it first (e.g. `git push -u origin <branch>`). This skill does not push branches itself.

### 2. Understand the change

Read the diff and commits holistically — not just the most recent commit. Ask yourself:

- What problem does this PR solve?
- What alternatives were considered? (Check commits, comments, and any related discussion.)
- What trade-offs did the approach make?
- How should a reviewer verify this works?

If anything is unclear from the diff alone, ask the user rather than guessing.

### 3. Draft the PR

**Title:** short (under 70 chars), sentence case, no conventional-commits prefix. Examples from this repo: *"First pass on costs savings by removing NAT Gateway"*, *"DBT database access"*, *"Uploads frontend"*.

**Body structure:**

```markdown
## One-liner

This PR <one-sentence summary of what the PR does>.

<If dependent on another PR: "Not to be merged before #N.">

## Context

- <Why this PR exists — backstory, motivation>
- <Bullet points; link to related PRs with #N>

## Technical Decisions

### <Decision topic>

- <What was chosen and why>
- <Alternatives considered and why rejected>
- <Trade-offs accepted>

## Testing

- <Steps a reviewer can follow to verify>
- <Include real commands, curl snippets, or screenshot placeholders where useful>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

Notes on the structure:

- Omit `## Technical Decisions` entirely if the PR is a simple, single-decision change — not every PR needs it.
- Optional `## TODOs` section (before `## Testing`) for known follow-ups you're deliberately deferring. Use subheadings per TODO.
- Be honest about trade-offs and limitations — this project's PRs routinely call out what's *not* being solved, and reviewers value that.

### 4. Confirm with the user

Show the drafted title and body. Ask: "Does this look right, or anything to adjust before I open the PR?" Wait for approval.

### 5. Open the PR

Once approved:

- Create the PR as a **draft** by default: `gh pr create --draft --title "..." --body "$(cat <<'EOF' … EOF)"`. Pass the body via heredoc to preserve formatting.
- If the user explicitly asked for ready-for-review, drop `--draft`.
- Return the PR URL.

## Do not

- Do not create the PR before the user has approved the draft.
- Do not invent testing steps you haven't verified are runnable — if you're unsure, ask the user how they tested it.
- Do not skip the Claude Code attribution footer.

---
name: pr
description: Create a pull request with a description matching the project's established format and style
disable-model-invocation: true
user-invocable: true
allowed-tools: Bash(git *) Bash(gh *) Read Grep Glob
argument-hint: "[base-branch]"
---

Create a pull request for the current branch, writing a description that matches the format and style of previously merged PRs in this repository.

## Steps

### 1. Gather context

Run these commands to understand the current state:

- `git status` — check for uncommitted changes
- `git log --oneline -1` — current branch's latest commit
- `git rev-parse --abbrev-ref HEAD` — current branch name
- Determine the base branch: use `$ARGUMENTS` if provided, otherwise default to `main`
- `git log --oneline <base-branch>..HEAD` — all commits on this branch
- `git diff <base-branch>...HEAD` — full diff against base

If there are uncommitted changes, warn the user and stop.

### 2. Fetch merged PR descriptions for style reference

Run:
```
gh pr list --state merged --limit 5 --json title,body
```

Study the format. This project uses a consistent structure with these sections:
- **## One-liner** — A single sentence summarising what the PR does
- **## Context** — Bullet-pointed background on _why_ this change is being made, what prompted it, and any relevant history
- **## Technical Decisions** — Key trade-offs or choices, each as a `### Sub-heading` with bullet-pointed explanation. Omit this section if there are no meaningful decisions to document.
- **## TODOs** — Known follow-ups or limitations, each as a `### Sub-heading`. Omit if there are none.
- **## Testing** — How to verify the change works. Can be manual steps, commands to run, or screenshots.

The tone is conversational and first-person. Use bullet points liberally. Reference other PRs/issues by number where relevant.

### 3. Draft the PR title and body

- **Title**: Short (under 70 characters), describes the change in plain language. Match the style of previous PR titles (e.g. "First pass on file uploads", "Document addition of new users and permissions setup").
- **Body**: Follow the section structure above. Write from the perspective of the author explaining their work to a reviewer. Be specific about _why_ decisions were made, not just _what_ changed.

### 4. Check remote state

- Verify the branch has been pushed: `git rev-parse --abbrev-ref --symbolic-full-name @{u}`
- If not pushed, push with: `git push -u origin <branch-name>`

### 5. Create the PR

Use `gh pr create` with a HEREDOC for the body:

```
gh pr create --title "the title" --body "$(cat <<'EOF'
...body...
EOF
)"
```

### 6. Report back

Print the PR URL.

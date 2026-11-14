---
name: raise-pr
description: Opens a GitHub PR in this repo's house style (One-liner / Context / Technical Decisions / Testing). Use when asked to raise, open, ship or put up a PR, even without naming this skill.
dependencies: git, gh (authenticated for this repo)
user-invocable: true
allowed-tools: Bash(git status:*) Bash(git branch:*) Bash(git log:*) Bash(git diff:*) Bash(git rev-parse:*) Bash(git fetch:*) Bash(git merge-base:*) Bash(gh pr list:*) Bash(gh pr view:*) Bash(gh pr create:*) Bash(gh pr edit:*) Bash(gh pr ready:*) Read Grep Glob
argument-hint: "[optional notes to include]"
---

# Raise PR

Turn the current branch into a draft pull request whose title and body read like the ones already in this repo. Tell the user you're running the `raise-pr` skill before you start.

The body explains **why**, not what: the diff already shows what changed. Spend the words on motivation, alternatives rejected, trade-offs accepted and what's deliberately not solved. The house voice is first person, plain and honest about limitations, with bullets over prose and no `feat:` / `fix:` prefixes.

Nothing leaves the machine without the user's say-so: draft first, push only on a yes, create only after the body is approved.

Plane is out of scope. Don't search for or reference work items.

## 1. Gather context

Run `git fetch origin` first, then these in parallel:

- `git status`: anything uncommitted?
- `git branch --show-current`
- `git rev-parse --abbrev-ref --symbolic-full-name @{u}`: the upstream, if any
- `git log origin/main..HEAD --oneline` and `git diff origin/main...HEAD` (three dots)
- `gh pr list --state merged --limit 3 --json title,body`: style reference
- `gh pr list --state open --json number,title,headRefName`: possible base PRs

Then decide:

- **Uncommitted changes:** ask whether to commit them first or leave them out.
- **No upstream, or upstream isn't `origin/<this branch>`:** propose `git push -u origin <branch>` and run it only if the user agrees.
- **Stacked on another open PR:** if `git merge-base --is-ancestor origin/<their headRefName> HEAD` succeeds for an open PR whose branch isn't in `origin/main`, ask whether to target that branch. If yes, diff against it instead of `origin/main`, pass `--base <their branch>` and add "Not to be merged before #N." under the One-liner.

## 2. Draft

Read every commit and the whole diff, not just the last commit. If the motivation or how it was tested isn't clear from the diff, commits or conversation, ask rather than guess. Fold in any notes passed as the argument.

**Title:** under 70 characters, sentence case, no prefix. Real examples: *"Process uploads as soon as the browser finishes uploading them"*, *"Uploads frontend"*, *"DBT database access"*.

**Body:**

```markdown
## One-liner

This PR <one sentence on what it does and the outcome>.

## Context

- <Why it exists: backstory, the problem, related PRs as #N>

## Technical Decisions

### <Decision>

- <What was chosen and why>
- <Alternatives considered and why they lost>
- <Trade-offs accepted>

## TODOs

### <Deferred follow-up>

- <What and why it's deferred>

## Testing

- <What was actually run, with real commands and results>
- <What hasn't been checked yet, said plainly>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

- Drop `## Technical Decisions` for a single-decision change, and `## TODOs` when nothing is deferred.
- Only list testing you've seen happen in this session or the user has described. Anything else goes in as "Not yet …".

## 3. Confirm

Show the title and body and ask: "Does this look right, or anything to adjust before I open the PR?" Wait for approval. If the user rewrites more than wording, ask what the draft got wrong and suggest adding it to Gotchas below.

## 4. Open

```bash
gh pr create --draft --title "<title>" --body "$(cat <<'EOF'
<body>
EOF
)"
```

Drop `--draft` only if the user asked for ready-for-review. Then run `gh pr view <n> --json isDraft,url` and return the URL.

## Gotchas

- `gh pr create --draft` has come back as a non-draft PR (#74). Always check `isDraft` afterwards and fix it with `gh pr ready <n> --undo`.
- A branch created with `git checkout -b <name> origin/main` tracks `origin/main`, so it looks as if it has an upstream. Check that the upstream is `origin/<branch>`, otherwise a push goes to main.
- Local `main` is often stale. Diff against `origin/main` after fetching, or the PR description picks up already-merged work.
- The generated API client (`apps/web/src/__generated__/`) and lockfiles swell the diff. Mention that they were regenerated; don't describe them.

## Example

Request: "open the PR" on a branch adding an upload-processing endpoint, after tests and a `docker compose` run in this session.

Output (trimmed from #75):

```markdown
Process uploads as soon as the browser finishes uploading them

## One-liner

This PR adds an endpoint the browser calls once a GPX file has landed in storage, which runs `process_upload` there and then, so uploads finally turn into hexagons on the map.

## Context

- Nothing has called `process_upload` since the AWS Lambda trigger was removed (#33), so every upload stays at `UPLOAD_PENDING`.
- #36 fixes this with a worker and a Tigris webhook. That's the better long-term shape, but it's ~1,000 lines with failing tests, so I wanted the smallest fix I fully understand.

## Technical Decisions

### Process in the request, triggered by the browser

- After the PUT succeeds, the web app calls `POST /api/v1/upload-processing-jobs`; 404 if it's not the caller's upload, 409 if the file isn't in storage yet.
- Trade-off accepted: the person waits while their file is processed (0.58 s for 570 KB locally). A worker is the fix once uploads grow.

## Testing

- `cd apps/backend && ENV=TEST uv run pytest`: 228 passed, including 7 new endpoint tests.
- End to end against `docker compose`: 409 before the upload, `UPLOAD_SUCCESS` with 18 hexagons after, no duplicates on a third call.
- Not yet clicked through in a browser.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---
name: manage-backlog
description: Keep the Backlog.md task in sync with the work actually happening — pick up the relevant task and mark it In Progress at the start of a session, keep its description/scope current as the work evolves, and mark it Done when a PR is opened. Use at the start of a work session and whenever task state has drifted from reality.
user-invocable: true
allowed-tools: mcp__backlog__get_backlog_instructions mcp__backlog__task_list mcp__backlog__task_search mcp__backlog__task_view mcp__backlog__task_edit Bash(git branch:*) Bash(git rev-parse:*) Bash(gh pr view:*)
---

You are keeping this project's Backlog.md tasks in step with the work in progress. The goal is that the board always reflects reality: the task being worked on is In Progress, its description matches the current scope, and it flips to Done the moment a PR goes up.

If you haven't already this session, read `backlog://workflow/overview` (or call `get_backlog_instructions`) so you follow the project's conventions.

## 1. Start of session — pick up a task, mark it In Progress

Work out what this session is about (the user's first request, the current branch via `git branch --show-current`, the diff so far) and match it to a Backlog task:

- `task_list` / `task_search` with keywords from the goal or branch name; `task_view` the likely candidate to confirm it's the right one.
- If one clearly matches and isn't already In Progress, set it: `task_edit` status → In Progress.
- If several could fit, or none is an obvious match, ask the user which task (if any) this maps to — don't guess, and don't grab an unrelated task just to have one in flight.
- If no task exists for the work, say so and ask whether to create one. Never create a task autonomously.

Remember which task you picked up — steps 2 and 3 act on that one.

## 2. During implementation — keep the description current

If the scope changes as you work — you uncover extra work, drop part of it, or the approach materially differs from what the task assumed — update the task so it still describes what's actually being done:

- `task_edit` the `description` (and acceptance criteria, when they no longer match the real scope).
- Record the *why* of a notable change with `notesAppend`, not just the *what*.
- Call out significant scope changes to the user as you make them — a quick "this task's scope is growing to include X, I've updated it" — so the board change isn't silent.

Small, in-scope adjustments don't need an edit; reserve this for genuine scope drift.

## 3. On PR open — mark it Done

When you open a PR for the work (including via the `raise-pr` skill), move the task to Done:

- `task_edit` status → Done, with a PR-style `finalSummary` (what changed, why, how it was tested) and the PR link added to `references`.
- Check off the acceptance criteria the change actually satisfies; leave unverified ones unchecked and say which.
- Only the task this session delivered — don't sweep other tasks to Done.

## Do not

- Don't create or archive tasks autonomously — propose, then let the user decide.
- Don't mark criteria or a whole task Done that you haven't actually verified; honest state beats a tidy board.
- Don't move a task you aren't actually working on.

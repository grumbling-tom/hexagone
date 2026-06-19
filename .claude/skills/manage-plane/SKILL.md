---
name: manage-plane
description: Keep the Plane work item in sync with the work actually happening — pick up the relevant item and mark it In Progress at the start of a session, keep its description/scope current as the work evolves, and mark it Done when a PR is opened. Use at the start of a work session and whenever item state has drifted from reality.
user-invocable: true
allowed-tools: mcp__plane__list_work_items mcp__plane__search_work_items mcp__plane__retrieve_work_item mcp__plane__update_work_item mcp__plane__list_modules Bash(git branch:*) Bash(git rev-parse:*) Bash(gh pr view:*)
---

You are keeping this project's Plane work items in step with the work in progress. The goal is that the board always reflects reality: the item being worked on is In Progress, its description matches the current scope, and it flips to Done the moment a PR goes up.

Tasks and milestones live in Plane, reached via the Plane MCP server (`.mcp.json`, tools prefixed `mcp__plane__`). A **Module** is a milestone/epic; a **Work Item** is a task associated to its module; statuses are Plane states (Todo / In Progress / Done).

## 1. Start of session — pick up a work item, mark it In Progress

Work out what this session is about (the user's first request, the current branch via `git branch --show-current`, the diff so far) and match it to a Plane work item:

- `search_work_items` with keywords from the goal or branch name (or `list_work_items` to browse); `retrieve_work_item` the likely candidate to confirm it's the right one.
- If one clearly matches and isn't already In Progress, set it: `update_work_item` state → In Progress.
- If several could fit, or none is an obvious match, ask the user which item (if any) this maps to — don't guess, and don't grab an unrelated item just to have one in flight.
- If no item exists for the work, say so and ask whether to create one. Never create a work item autonomously.

Remember which item you picked up — steps 2 and 3 act on that one.

## 2. During implementation — keep the description current

If the scope changes as you work — you uncover extra work, drop part of it, or the approach materially differs from what the item assumed — update it so it still describes what's actually being done:

- `update_work_item` the description (and acceptance criteria, when they no longer match the real scope).
- Call out significant scope changes to the user as you make them — a quick "this item's scope is growing to include X, I've updated it" — so the board change isn't silent.

Small, in-scope adjustments don't need an edit; reserve this for genuine scope drift.

## 3. On PR open — mark it Done

When you open a PR for the work (including via the `raise-pr` skill), move the item to Done:

- `update_work_item` state → Done, with a short summary of what changed and how it was tested, and the PR link added as a work-item link.
- Check off the acceptance criteria the change actually satisfies; leave unverified ones unchecked and say which.
- Only the item this session delivered — don't sweep other items to Done.

## Do not

- Don't create or delete work items autonomously — propose, then let the user decide.
- Don't mark criteria or a whole item Done that you haven't actually verified; honest state beats a tidy board.
- Don't move an item you aren't actually working on.

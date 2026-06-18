---
id: TASK-0020
title: 'Backend: predicate reads & guarded writes (two-Protocol typing)'
status: Done
assignee: []
created_date: '2026-06-18 12:01'
updated_date: '2026-06-18 13:04'
labels: []
dependencies: []
references:
  - 'https://github.com/grumbling-tom/hexagone/pull/63'
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The repository's `Filter` predicates currently only guard reads (`get_filtered`). Writes are unguarded: `archive_group`/`update_group` do a permissioned read then a separate mutate (a check-then-act race), and `add_member` inserts membership rows with no enforced row invariant. A FIXME notes the permission layer can't distinguish READ from WRITE.

Introduce guarded writes with static guarantees. Predicates become a nominal Pydantic base (`Predicate`) plus two structural `typing.Protocol`s: `Filter` (renders to SQL via `to_sql`, used for reads and atomic `UPDATE … WHERE`) and `Guard` (`is_satisfied_by` in-memory check, used for `INSERT` where there is no row to filter). SQL-only predicates (`Or`, `Related`) deliberately omit `is_satisfied_by`, so the type checker rejects them as create-guards. Repository gains an atomic `update(uid, values, guards)` and a guarded `create(obj, guards)`; permissions become operation-aware (`permissions_predicates(user, entity, operation)` with a READ/WRITE `Operation`). Concretes are renamed from `*Filter` to unsuffixed (`Equals`, `In`, `Or`, `Related`, …) and `filters.py` becomes `predicates.py`.

Outcome: the type checker statically verifies the right kind of predicate reaches each repository method, and group mutations are authorized atomically.</description>
<parameter name="milestone">Admin page
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Predicate hierarchy splits into a nominal `Predicate` base plus `Filter` and `Guard` runtime_checkable Protocols; SQL-only predicates (`Or`, `Related`) omit `is_satisfied_by` while dual-mode ones define it
- [x] #2 Repository exposes atomic `update(uid, values, guards: Filter)` (UPDATE … WHERE … RETURNING) and `create(obj, guards: Guard)` raising `NotAuthorizedError` on guard failure; `delete` still works
- [x] #3 `permissions_predicates(user, entity, operation)` with a READ/WRITE `Operation` enum replaces `permission_filters`; WRITE on UserGroup is owner-only
- [x] #4 `archive_group`/`update_group` use the atomic guarded `update`; `add_member(db, actor, group_uid, member_uid)` enforces relational authz via a permissioned read plus a same-row create guard
- [x] #5 All `*Filter` concretes renamed to unsuffixed names and `filters.py` renamed to `predicates.py`, with all call sites and tests updated
- [x] #6 Type checker passes and flags `create(guards=[Related/Or])` as errors while allowing the `update` equivalents; full pytest suite (repository, permissions, user_group, router tests) green
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Split the repository predicate hierarchy into a nominal Pydantic base (`Predicate`) plus two `runtime_checkable` Protocols — `Filter` (`to_sql`) and `Guard` (`is_satisfied_by`) — used only as method parameter annotations. The discriminator is method presence: dual-mode concretes (`Equals`, `In`, `Range`, …) define `is_satisfied_by`; SQL-only ones (`Or`, `Related`) omit it, so passing them to `create(guards=...)` is a static type error while the `update` equivalents type-check fine.

Repository gained atomic `update(uid, values, guards: Filter)` (UPDATE … WHERE … RETURNING, `synchronize_session=False` + `populate_existing=True`) and guarded `create(obj, guards: Guard)` raising `NotAuthorizedError`; `delete` kept working with its trivial logic inlined. Permissions became operation-aware (`permissions_predicates(user, entity, operation)` with a READ/WRITE `Operation`; WRITE on UserGroup is owner-only). `archive_group`/`update_group` now mutate atomically (archive keeps the `archived == False` idempotency guard); `add_member(db, actor, group_uid, member_uid)` enforces relational authz via a permissioned WRITE read plus a same-row create guard. `filters.py` renamed to `predicates.py` and all `*Filter` concretes renamed unsuffixed across call sites and tests.

Tested: pyright 0 errors (probe confirmed `create(guards=[Related/Or])` flagged, `update` equivalents pass); ruff clean; 72 relevant tests pass (repository/permissions/user_group/router/architectural). The 9 LocalStack-dependent upload/health tests were not run (unrelated). PR #63 (draft).
<!-- SECTION:FINAL_SUMMARY:END -->

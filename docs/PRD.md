# Hexagone — Product Requirements Document (PRD)

## 1. Product Overview

**Product name:** Hexagone
**Platform:** Mobile-first web app, usable on desktop. Native apps are a later phase.
**Product stage:** Closed beta with one group of friends (fewer than 10 runners) who live in different places, invite-only, hosted on the Mac mini. Later phases each get their own PRD (see §8).
**Launch market:** United Kingdom and Canada
**Primary user:** Friends and small running clubs who run separately, often in different towns or countries, but want a shared, ongoing competition. Individual, competitive and exploration-minded runners are future audiences; this PRD concentrates on the friends group or club.

### Product Vision

> **Hexagone turns the runs a group already does into a territory game played on the map of their own streets.**

Every hexagon a runner's route passes through becomes theirs, and so does every hexagon inside a loop they close, until someone else claims it more recently. The map becomes a shared, living scoreboard that rewards running somewhere new and running back to defend what you hold.

Hexagone sits on top of what runners already do:

- **Watches and running apps** (Garmin, Apple Watch, Strava) keep recording the run. Hexagone only needs the GPS file.
- **Hexagone** owns territory: who holds which hexagon, who took it from whom, and how each runner ranks in the group and overall.
- **The group's chat** stays where people talk. Hexagone gives them something to talk about.

---

## 2. Problem Statement

> Runners in a friends group or small club run separately most of the week and only compare distance and pace in apps like Strava. Their routes become repetitive, the group has nothing it is building or competing over together, and pace-based comparisons favour the fastest runner, so most members never feel in contention. Today they keep motivation up through chat banter and the occasional organised run, which fades quickly.

**Short Version**

> We believe groups of runners lose motivation because their solo runs feed no shared game: there is no reason to try a new route, nothing the group competes over together, and existing comparisons reward speed rather than effort and curiosity.

---

## 3. Product Goals

Hexagone should help a group of runners:

1. Turn each run into visible progress on a map they share.
2. Find a reason to run new routes rather than the same loop.
3. Compete in a way that rewards consistency and exploration, not only speed.
4. Know when someone has taken their territory, and by whom.
5. See where they stand in their group and against everyone on Hexagone.
6. Keep using the watch or running app they already have.
7. Reduce questions such as:

- "Who's got the park now?"
- "Did anyone take my hexes this week?"
- "Where haven't I run yet?"
- "Who's leading the group?"

---

## 4. Non-Goals

The closed beta will not attempt to:

- Replace Strava, Garmin Connect or other training apps.
- Analyse pace, heart rate, training load or fitness.
- Plan or suggest routes.
- Sync runs automatically (Strava sync is the next phase; Garmin and Apple Health follow).
- Offer native iOS or Android apps.
- Open sign-up to the public.
- Hide a runner's home area with privacy zones (accepted for a group of friends; required before the wider beta, see §21).
- Offer weekly or monthly leaderboards (all time only).
- Let groups compete for territory as teams.
- Provide a social feed, comments or chat.
- Send email or push notifications for game events.

The beta stays focused on **territory, competition and the group**.

---

## 5. Target User / Proto-Persona

### Alex — Social Club Runner

**Age:** 25–45
**Occupation:** Full-time professional
**Situation:** Runs three or four times a week, mostly alone, and belongs to a group of friends who share a group chat. Some friends live nearby and run together now and then; others live in other cities or countries.

Alex records every run on a watch and uploads it to Strava, but rarely looks at the stats beyond distance. They are not the fastest in the group and do not want to be judged on pace.

The group already:

- Shares runs and screenshots in the chat.
- Runs together when they're in the same place.
- Teases each other about who is slacking.

**Alex's Goals**

Alex wants to:

- Have a reason to vary their route.
- See their runs add up to something.
- Beat friends at something that rewards effort, not speed.
- Know when a friend has encroached on "their" streets.
- Take territory back.

**Current Behaviours**

Alex currently relies on:

- A GPS watch (Garmin, Apple Watch or similar).
- Strava.
- The group chat.
- Habit: the same two or three routes from home.

The problem is not a lack of tracking. It is that tracked runs feed nothing shared and nothing that changes where they run.

---

## 6. Jobs to Be Done

### Primary Job

> When I finish a run, show me what it won me on a map my friends also play on, so that every run feels like a move in a game we share.

### Supporting Jobs

When I plan a run, help me see where I could claim new ground or take some back.

When a friend takes my territory, tell me who and how much, so I can take it back.

When my group wants to know who is winning, give us a ranking that rewards both holding ground and exploring.

When I join a group, let me start playing straight away from a link a friend sent me.

---

## 7. Product Principles

### 7.1 Build On the Run, Not Around It

Hexagone should never ask a runner to change how they record a run. A GPS file from any watch or app is enough.

---

### 7.2 Territory Over Speed

Rankings reward ground held and ground explored. Pace and distance are context, never the score.

---

### 7.3 Most Recent Wins

A hexagon belongs to whoever most recently ran a loop around it. Territory is never permanent, so there is always something to defend and something to take.

---

### 7.4 Every Run Counts Somewhere

A run should always show the runner something: hexagons claimed, hexagons taken back, or the reason it didn't count (for example, it was recorded before they joined).

---

### 7.5 Low Effort

Common actions should take seconds:

- Upload a run.
- See what a run claimed.
- Switch between the global map and a group's map.
- Copy a group invite link.
- Check the leaderboard.

---

### 7.6 Mobile-First

Runners check Hexagone on their phone after a run. Every screen must work at phone width first.

---

## 8. Beta Scope and Phases

The closed beta will include:

1. Passwordless sign-in.
2. Joining by group invite link, without being added to the allowlist by hand.
3. GPX upload, with processing status and the reason a run was rejected.
4. Claiming the hexagons a route passes through and the hexagons inside any closed loop.
5. "Most recent wins" ownership, by run time.
6. Global and per-group ownership.
7. A map with global and group views.
8. Groups: create, invite, join, leave, manage, belong to several.
9. Two all-time leaderboards, Territory and Explorer, globally and per group.
10. In-app lost-hex alerts, one per run.
11. A dashboard with weekly stats, streak and latest run.

**Phases after the beta** (each gets its own PRD):

| Phase | Audience | Adds |
| --- | --- | --- |
| Closed beta (this PRD) | One friends group, fewer than 10 runners | Everything above, GPX upload only |
| Invite-only beta | Several clubs and groups, early-access requests approved by hand | Strava sync, privacy zones |
| Public launch | Anyone | Open sign-up, Garmin and Apple Health sync |

Screen wireframes are in [`resources/README.md`](../resources/README.md).

---

## 9. Information Architecture

Hexagone uses a bottom navigation bar on phones (a top bar on desktop) with four sections: **Dashboard**, **Map**, **Leaderboards** and **Groups**. **Uploads** opens from the upload button on the Dashboard and the Map. The in-app notification list opens from a bell in the top bar.

### Dashboard

Shows:

- This week's hexes claimed and distance, with all-time totals underneath.
- Week streak.
- Total hexes held.
- The latest run on a small map: hexes it claimed and hexes it took from others.
- A short leaderboard extract for the runner's main group.
- **Upload a run**.

### Map

Shows:

- Hexagons coloured by owner: mine, others', and ones I've lost recently.
- A scope switch: **Everyone** or one of my groups.
- Tapping a hexagon shows its owner and when they claimed it.
- Small hexagons at street level, larger ones as I zoom out, with **Contested** shown where no one owns most of an area.

### Leaderboards

Shows:

- **Territory**: hexes currently held.
- **Explorer**: unique hexes ever claimed.
- A scope switch: **Everyone** or one of my groups.
- My own position, even when I'm outside the top of the list.

### Groups

Shows:

- My groups, each with member count and my rank.
- Create a group.
- Inside a group: members, the invite link (copy), and, for admins, rename, remove members, make admin and archive.
- Leave a group.

### Uploads

Shows:

- Every run I've uploaded, newest first, with its status (processing, claimed N hexes, or the reason it was rejected).

---

## 10. Epic 1 — Sign-In and Access

*Built today: passwordless magic-link sign-in, limited to an email allowlist.*

### User Story 1.1 — Sign In

**As a** runner,
**I want to** sign in with just my email,
**so that** I don't need another password.

**Acceptance Criteria**

**Scenario: Allowed email**

- **Given** my email is allowed to sign in
- **When** I enter it on the sign-in page
- **Then** I receive a one-time sign-in link valid for 10 minutes
- **And** opening it in the same browser signs me in.

**Scenario: Email not allowed**

- **Given** my email is not allowed and I have no invite link
- **When** I enter it
- **Then** Hexagone tells me it is invite-only and offers **Request early access**.

---

### User Story 1.2 — Join From an Invite Link

**As a** friend of a group member,
**I want to** open the invite link they shared and start playing,
**so that** joining doesn't depend on someone editing a list.

**Acceptance Criteria**

**Scenario: New runner**

- **Given** I've never signed in
- **When** I open a valid group invite link and sign in with my email
- **Then** my email is allowed from then on
- **And** I'm added to that group
- **And** I'm asked for a display name (User Story 1.3), then prompted to upload a run.

**Scenario: Existing runner**

- **Given** I already have an account
- **When** I open a valid invite link
- **Then** I'm added to the group and taken to its map.

**Scenario: Invalid link**

- **Given** the link has been reset or the group archived
- **When** I open it
- **Then** Hexagone says the link no longer works and asks me to get a new one from the group.

*Assumption: an invite link works until an admin resets it. Expiry and use limits are open questions (§30).*

---

### User Story 1.3 — Choose a Display Name

**As a** runner,
**I want to** choose the name other runners see,
**so that** friends recognise me on the leaderboards, the map and alerts without seeing my email.

**Acceptance Criteria**

**Scenario: First sign-in**

- **Given** I'm signing in for the first time
- **When** I reach the welcome page
- **Then** I'm asked for a display name before uploading a run.

**Scenario: Change it later**

- **Given** I've set a display name
- **When** I change it in settings
- **Then** the new name shows everywhere, including past alerts.

*Built today: the account stores only an email, so display names need adding (BR-11).*

---

## 11. Epic 2 — Uploading Runs

*Built today: GPX upload from the welcome and uploads pages, processed as soon as the file lands (#75).*

### User Story 2.1 — Upload a Run

**As a** runner,
**I want to** upload the GPX file from my watch or running app,
**so that** the run claims hexagons.

**Acceptance Criteria**

**Scenario: Valid run**

- **Given** I'm signed in
- **When** I upload a GPX file
- **Then** I see it processing
- **And** then how many hexes it claimed and how many it took from others.

**Scenario: Invalid file**

- **Given** the file is not valid GPX
- **When** processing finishes
- **Then** I see the reason in plain words (for example, "invalid GPX").

**Scenario: No closed loop**

- **Given** the run is an out-and-back or point-to-point route with no closed loop
- **When** processing finishes
- **Then** it still claims every hexagon the route passed through.

**Scenario: Duplicate run**

- **Given** I've already uploaded a run that started at 07:02
- **When** I upload a run that starts within a minute of it (for example, the same run exported from Strava as well as Garmin)
- **Then** Hexagone tells me it's already uploaded and doesn't process it again (BR-05).

The upload page says that only runs count. This isn't enforced in the beta (BR-12).

*Technical note: the backend caps a file at 10 MB, and also caps GPS points, loops and hexagons per file. These protect the server, because a file is processed while the runner waits. A watch recording every second produces about 2 MB for a 4-hour marathon, so the cap is only reached by runs of around 20 hours, and the PRD treats it as a safeguard rather than a product limit.*

---

### User Story 2.2 — Upload an Older Run

**As a** runner,
**I want to** know whether an old run will count,
**so that** I'm not surprised when it claims nothing.

**Acceptance Criteria**

**Scenario: Run from before I joined**

- **Given** a run completed before I joined Hexagone
- **When** I upload it
- **Then** it is saved to my uploads
- **And** it claims no hexagons
- **And** Hexagone tells me that only runs since I joined count (BR-04).

**Scenario: Run after I joined, uploaded late**

- **Given** a run completed after I joined but uploaded days later
- **When** it is processed
- **Then** it only takes hexagons from claims made before the run happened (BR-02).

---

### User Story 2.3 — See My Uploads

**As a** runner,
**I want to** see every run I've uploaded and its outcome,
**so that** I know which ones counted.

**Acceptance Criteria**

- **Given** I've uploaded runs
- **When** I open Uploads
- **Then** I see each run, newest first, with its date, status and hexes claimed.

*Runners can't delete uploads in the beta. A mistaken upload is removed by hand on request (BR-13).*

---

## 12. Epic 3 — Claiming and Ownership

*Built today: claims for hexagons inside closed loops, per runner. To build: claims for hexagons on the route, ownership by run time, and global and group scopes.*

### User Story 3.1 — Claim Hexagons

**As a** runner,
**I want** my run to claim the hexagons I ran through and the hexagons inside any loop I closed,
**so that** the ground I cover, and the ground I run around, becomes mine.

**Acceptance Criteria**

**Scenario: Hexagons on the route**

- **Given** my run passes through hexagons
- **When** it is processed
- **Then** each of them is claimed by me as of the time I passed through it (BR-01).

**Scenario: Hexagons inside a loop**

- **Given** my run closes a loop (BR-01)
- **When** it is processed
- **Then** every hexagon inside the loop is also claimed by me, as of the time the loop closed.

---

### User Story 3.2 — Take a Hexagon

**As a** runner,
**I want to** take a hexagon by running around it after someone else,
**so that** territory stays contested.

**Acceptance Criteria**

**Scenario: Taking from another runner**

- **Given** another runner owns a hexagon
- **When** my run passes through or encloses it after their claim
- **Then** I own it (BR-02).

**Scenario: Older run doesn't take**

- **Given** another runner claimed a hexagon on Tuesday
- **When** I upload a run from Monday that passes through or encloses it
- **Then** they keep it
- **And** my Monday claim still counts for the Explorer board.

---

### User Story 3.3 — Ownership Depends on Scope

**As a** group member,
**I want** my group's map to show who owns each hexagon among us,
**so that** our group game isn't decided by strangers.

**Acceptance Criteria**

- **Given** runner 1 (group A) claims a hexagon and runner 2 (group B, not in group A) later claims it
- **When** anyone views the **Everyone** map or leaderboard
- **Then** runner 2 owns it
- **And** on group B's map runner 2 owns it
- **And** on group A's map runner 1 still owns it (BR-03).

---

## 13. Epic 4 — The Map

*Built today: a personal map of the signed-in runner's hexagons, loading at most 1,000.*

### User Story 4.1 — See the Map

**As a** runner,
**I want to** see hexagons coloured by who owns them,
**so that** I can see where I hold ground and where I could take it.

**Acceptance Criteria**

**Scenario: Everyone view**

- **Given** I open the Map
- **When** **Everyone** is selected
- **Then** I see every claimed hexagon, coloured as mine or someone else's.

**Scenario: Group view**

- **Given** I belong to a group
- **When** I select it
- **Then** I see ownership among that group's members only.

**Scenario: Every hexagon in view**

- **Given** I'm viewing any part of the map
- **When** it loads
- **Then** every claimed hexagon in view is shown, however many there are
- **And** only the hexagons in view are loaded, so the map stays quick on a phone.

*Today the map loads a runner's whole territory, stopping at the first 1,000 hexagons, whatever part of the map is showing. This criterion makes sure that gets fixed.*

---

### User Story 4.2 — Inspect a Hexagon

**As a** runner,
**I want to** tap a hexagon to see who owns it and since when,
**so that** I know who to take it from.

**Acceptance Criteria**

- **Given** I'm viewing the Map
- **When** I tap a claimed hexagon
- **Then** I see the owner's display name and the date of the run that claimed it.

**Scenario: Zoomed out**

- **Given** I'm zoomed out and hexagons are shown at a coarser size (User Story 4.3)
- **When** I tap one
- **Then** I see who owns the most of it and how much of it I own
- **And** I can zoom in to it.

---

### User Story 4.3 — Zoom From Street to City

**As a** runner,
**I want** the hexagons to stay readable as I zoom out from my street to my whole city,
**so that** I can see both the detail of a run and the shape of everyone's territory.

**Acceptance Criteria**

**Scenario: Street level**

- **Given** I'm zoomed in to street level
- **When** the map draws
- **Then** I see the resolution 11 hexagons the game is played on.

**Scenario: Zoomed out**

- **Given** I zoom out
- **When** the small hexagons would become too small or too many to draw
- **Then** the map shows larger hexagons instead, each one standing for the small hexagons inside it (BR-14)
- **And** the number of hexagons on screen stays roughly the same at every zoom.

**Scenario: Mixed ownership**

- **Given** a larger hexagon contains small hexagons with different owners
- **When** one runner owns more than half of them
- **Then** it is coloured by that runner
- **And** when no one does, it is shown with a **Contested** pattern.

*Zoom changes only what is drawn. Claims, ownership and leaderboards always use resolution 11.*

---

## 14. Epic 5 — Groups

*Built today: the API to create, rename and archive groups and manage members. No screens.*

### User Story 5.1 — Create a Group

**As a** runner,
**I want to** create a group for my friends or club,
**so that** we have our own map and leaderboard.

**Acceptance Criteria**

- **Given** I'm signed in
- **When** I create a group with a name
- **Then** the group exists with me as its admin
- **And** I'm shown its invite link to share.

---

### User Story 5.2 — Invite Friends

**As a** group member,
**I want to** copy the group's invite link,
**so that** I can send it to friends by email or chat and they can join in one step.

**Acceptance Criteria**

- **Given** I'm a member of a group
- **When** I tap **Copy invite link**
- **Then** the link is copied and Hexagone confirms it.

*Hexagone does not send invite emails or open the phone's share sheet in the beta; members paste the link wherever they like.*

---

### User Story 5.3 — Belong to Several Groups

**As a** runner,
**I want to** be in my club and my friends' group at once,
**so that** I can play in both.

**Acceptance Criteria**

- **Given** I belong to several groups
- **When** I use the Map or Leaderboards
- **Then** I can switch between **Everyone** and each of my groups.

---

### User Story 5.4 — Manage a Group

**As a** group admin,
**I want to** rename the group, remove members, make others admins, reset the invite link and archive the group,
**so that** the group stays as intended.

**Acceptance Criteria**

**Scenario: Remove a member**

- **Given** I'm an admin
- **When** I remove a member
- **Then** they leave the group's map and leaderboards
- **And** ownership on the group's map is recalculated among the remaining members (BR-07).

**Scenario: Last admin**

- **Given** I'm the only admin
- **When** I try to leave
- **Then** Hexagone asks me to make someone else an admin, or archive the group, first.

---

### User Story 5.5 — Leave a Group

**As a** group member,
**I want to** leave a group,
**so that** I only play where I want to.

**Acceptance Criteria**

- **Given** I'm a member and not the last admin
- **When** I leave
- **Then** I no longer see the group
- **And** my global territory is unaffected.

---

## 15. Epic 6 — Leaderboards

*To build. The analytics plan ([`analytics-architecture.md`](analytics-architecture.md)) proposes serving leaderboards from dbt models.*

### User Story 6.1 — Territory Leaderboard

**As a** runner,
**I want to** see who holds the most hexagons,
**so that** I know who to chase.

**Acceptance Criteria**

- **Given** I open Leaderboards
- **When** **Territory** is selected
- **Then** runners are ranked by hexagons currently held in the selected scope (BR-08)
- **And** my position is shown even if I'm not near the top.

---

### User Story 6.2 — Explorer Leaderboard

**As a** runner,
**I want to** see who has run around the most ground,
**so that** exploring is rewarded even when I lose territory.

**Acceptance Criteria**

- **Given** I open Leaderboards
- **When** **Explorer** is selected
- **Then** runners are ranked by unique hexagons they've ever claimed (BR-08).

---

### User Story 6.3 — Switch Scope

**As a** runner,
**I want to** switch the leaderboards between everyone and each of my groups,
**so that** I can see where I stand in each.

**Acceptance Criteria**

- **Given** I belong to groups
- **When** I choose a scope
- **Then** both leaderboards show only runners in that scope, with ownership calculated within it (BR-03).

---

## 16. Epic 7 — Lost-Hex Alerts

*To build.*

### User Story 7.1 — Know When I've Lost Territory

**As a** runner,
**I want to** be told when someone's run takes my hexagons,
**so that** I can go and take them back.

**Acceptance Criteria**

**Scenario: Hexes taken**

- **Given** I own hexagons
- **When** another runner's run takes some of them
- **Then** I get one in-app notification for that run: "Sam took 14 of your hexes on Tuesday's run"
- **And** opening it shows those hexagons on the Map.

**Scenario: Several runs**

- **Given** two runs took my hexagons
- **When** I open notifications
- **Then** I see one notification per run, newest first.

**Scenario: Unread count**

- **Given** I have unread notifications
- **When** I'm anywhere in the app
- **Then** the bell shows how many.

*Assumption: alerts follow global ownership, since a loss in any group is also a global loss. Whether group-only losses need their own alert is an open question (§30).*

---

## 17. Epic 8 — Dashboard

*To build. The design is in [`hexagone-dashboard-example.excalidraw.svg`](../resources/hexagone-dashboard-example.excalidraw.svg).*

### User Story 8.1 — See My Week

**As a** runner,
**I want to** see what I've done this week at a glance,
**so that** I feel progress after each run.

**Acceptance Criteria**

- **Given** I've uploaded runs this week
- **When** I open the Dashboard
- **Then** I see hexes claimed and distance this week, with all-time totals underneath
- **And** my week streak (consecutive weeks with at least one counted run)
- **And** total hexes currently held.

---

### User Story 8.2 — See My Latest Run

**As a** runner,
**I want to** see what my latest run won,
**so that** I get the payoff straight after uploading.

**Acceptance Criteria**

- **Given** I've uploaded a run
- **When** I open the Dashboard
- **Then** I see it on a small map with new hexes and hexes taken from others highlighted.

---

## 18. Ownership Model

Each hexagon has one owner per scope:

| Scope | Owner |
| --- | --- |
| Everyone | The runner with the latest eligible claim on it, among all runners |
| A group | The runner with the latest eligible claim on it, among that group's current members |

A claim's time is when the run passed through the hexagon, or when the loop that enclosed it was completed, not when the file was uploaded.

| Event | Effect |
| --- | --- |
| A run claims an unowned hexagon | The runner owns it in every scope they belong to |
| A run claims a hexagon after someone else's latest claim | Ownership moves to the runner in every scope containing both of them, and in Everyone |
| A run claims a hexagon before someone else's latest claim | No change in ownership; the claim still counts for Explorer |
| A runner leaves or is removed from a group | That group's ownership is recalculated without them |

**Lost recently** (shown on the Map) is an indicator, not a state: a hexagon I owned in that scope within the last 7 days.

---

## 19. Business Rules

### BR-01 — Claiming by Route and by Loop

A run claims two kinds of hexagon:

- **Route hexagons:** every hexagon the route line crosses, even briefly, claimed at the time the runner crossed it. GPS drift of 5–10 m is well under a hexagon's width at resolution 11, so a route only occasionally clips a neighbouring hexagon; that is accepted for the beta.
- **Enclosed hexagons:** every hexagon whose centre falls inside a closed loop, claimed at the time the loop closed. A loop closes when the route returns to within 10 m of an earlier point at least 50 m of route behind it.

Both count equally for ownership and both leaderboards. A run with no closed loop still claims its route hexagons. Hexagons are H3 cells at resolution 11, about 2,150 m² each with edges of about 29 m: roughly a street with its pavements. *The code uses resolution 10 today (about 0.015 km², edges about 76 m); the beta moves it to 11.* A 5 km test run claims 165 hexagons at resolution 11, against 32 at 10 and 1,014 at 12. Resolution 11 was chosen because it follows the route closely while staying coarse enough to blur exact positions.

---

### BR-02 — Most Recent Wins, by Run Time

The owner of a hexagon is whoever has the latest claim on it, timed by when their loop was completed. Uploading an older run never takes a hexagon from a later claim.

If two claims have the same completion time, the one processed first keeps the hexagon.

---

### BR-03 — Ownership Is Scoped

Ownership is calculated separately for **Everyone** and for each group, using only the claims of runners in that scope. A runner can own a hexagon in one group while someone outside that group owns it globally.

---

### BR-04 — Only Runs Since Joining Count

A run claims hexagons only if it was completed after the runner's account was created. Older runs are saved to the runner's uploads but claim nothing, for any board.

---

### BR-05 — Duplicate Uploads

A run that starts within one minute of a run the same runner has already uploaded is treated as a duplicate: it is saved as rejected, with the reason "already uploaded", and claims nothing. This catches the same file uploaded twice and the same run exported from two apps.

---

### BR-06 — Group Roles

The runner who creates a group is its admin. Admins can rename it, remove members, make other members admins, reset the invite link and archive it. Every member can share the invite link and leave. A group always has at least one admin.

---

### BR-07 — Group Membership Changes

Joining or leaving a group never changes global ownership. A group's ownership and leaderboards only ever use its current members' claims.

---

### BR-08 — Leaderboard Definitions

- **Territory** = hexagons a runner currently owns in the scope.
- **Explorer** = unique hexagons a runner has ever claimed with eligible runs (BR-04), whether or not they still own them.

Both count hexagons, with route and enclosed hexagons counted equally. Both are all time for the beta. Points (for example, different values for route and enclosed hexagons) may come in a later iteration.

---

### BR-09 — Invite Links

Each group has one invite link. Opening it and signing in lets a new email sign in from then on and adds the runner to the group. Resetting the link stops the old one working. Archiving a group stops its link working.

---

### BR-10 — Visibility

Every signed-in runner can see the **Everyone** map and leaderboards, including other runners' display names and territory. Group maps and leaderboards are visible only to that group's members.

---

### BR-11 — Display Names

Every runner has a display name, asked for on first sign-in and changeable in settings. It is what other runners see everywhere; email addresses are never shown.

---

### BR-12 — Runs Only, on Trust

Only runs should be uploaded. GPX files don't reliably say whether a route was run, walked or cycled, so the beta relies on the group's honour and doesn't check.

---

### BR-13 — Uploads Can't Be Deleted

Runners can't delete uploads in the beta. If a run was uploaded by mistake, it is removed by hand on request, and ownership of every hexagon it claimed goes back to whoever had the latest remaining claim.

---

### BR-14 — Map Resolution Follows Zoom

The map draws hexagons at a resolution that suits the zoom level, from resolution 11 at street level to coarser resolutions further out. Each coarser hexagon is the H3 parent of the resolution 11 hexagons inside it. It is coloured by the runner who owns more than half of those hexagons in the current scope, or shown as **Contested** when no runner does. Unclaimed small hexagons don't count towards that half. This is display only: the game is always scored at resolution 11.

*Technical note: the coarser views can be built as summary tables per resolution from the claims, which fits the dbt plan in [`analytics-architecture.md`](analytics-architecture.md).*

---

## 20. Mobile UX Requirements

Runners should be able to:

- Upload a run in no more than two taps from the Dashboard.
- See what a run claimed without leaving the upload screen.
- Switch map or leaderboard scope in one tap.
- Copy a group invite link in one tap.
- See their own leaderboard position without scrolling.
- Tell their hexagons from others' without relying on colour alone.

**Accessibility Requirements**

Hexagone should support:

- Dynamic text sizing.
- Screen-reader labels, including a text summary of the map (hexes held, hexes in view).
- Large touch targets.
- High-contrast map colours.
- Plain-language labels.
- Status shown with text or pattern as well as colour.

The target standard is **WCAG 2.2 AA**.

---

## 21. Privacy Requirements

Because GPS tracks reveal where people live and run:

- Raw GPX files are visible only to the runner who uploaded them.
- Other runners see hexagons and display names only, never routes, times of day or the GPX file.
- Email addresses are never shown to other runners, and are masked in logs.
- Group maps and leaderboards are visible only to group members.
- A runner can ask for their data to be exported or deleted. In the beta this is handled by hand within one month, as UK GDPR and PIPEDA require.
- Resolution 11 hexagons (about 29 m edges) blur a runner's exact route and doorstep a little, but still show which street they run on.
- The beta accepts that a runner's hexagons may reveal their home area to the group. **Privacy zones are required before the invite-only beta**, because it adds runners who don't know each other.

---

## 22. Notification Strategy

Hexagone sends only **in-app** notifications in the beta, and only for events a runner can act on:

- Someone took your hexagons (one per run).

Everything else (a friend's run, leaderboard changes) shows on the Dashboard, Map and Leaderboards rather than as a notification. Sign-in emails are the only emails.

---

## 23. Key User Flow — Joining and First Run

Alex creates **Tuesday Night Runners**, copies the invite link and pastes it into the group chat.

Sam opens the link on their phone, enters their email and opens the sign-in link.

Sam lands on the welcome page, enters the display name **Sam**, and uploads last night's run from Garmin Connect.

Hexagone shows:

> **Your run claimed 23 hexes.**

Sam opens the Map, switches to **Tuesday Night Runners** and sees their 23 hexagons next to Alex's.

On the Leaderboards, Sam is fourth on Territory and third on Explorer.

---

## 24. Key User Flow — Taking Territory Back

On Tuesday, Sam runs a loop around the park Alex has held for a month and uploads it.

Alex's bell shows **1**. The notification reads:

> **Sam took 14 of your hexes on Tuesday's run.**

Alex opens it and sees the 14 hexagons marked **Lost recently** on the Map.

On Thursday, Alex runs a wider loop around the park and uploads it.

Hexagone shows:

> **Your run claimed 31 hexes, including 14 taken from Sam.**

Sam gets the alert. The park has changed hands twice in a week, and nobody had to run faster to do it.

---

## 25. Success Metrics

The beta has fewer than 10 runners in different places, so hexagons will only change hands where members' running overlaps. Metrics are read as counts and trends, alongside conversations with the group, not as statistically significant rates.

**Changed Routes**

Measure:

- Share of runs that claim at least one hexagon the runner had never claimed before.
- Unique hexagons claimed per runner per week (Explorer growth).
- Share of runs that take back a hexagon the runner had lost.

**Live Competition**

Measure:

- Hexagons changing hands per week, in the group and globally.
- Share of active runners who both took and lost hexagons in a week.
- Median time between losing a hexagon and taking it back.

**Activity (context, not a target)**

Measure:

- Weekly active runners.
- Runs uploaded per runner per week.
- Uploads rejected, and why.

---

## 26. Outcome Metrics

Through conversations with the group, find out whether Hexagone helps runners:

- Choose routes to claim or take back hexagons, rather than running their usual loops.
- Feel in contention regardless of pace.
- Talk about the game in the group chat.
- Run more often, or keep running when motivation would otherwise dip.

---

## 27. Beta Prioritisation

| Priority | Capability | State today |
| --- | --- | --- |
| P0 | Passwordless sign-in | Built |
| P0 | Display name, asked on first sign-in and changeable | To build |
| P0 | GPX upload and processing, with rejection reasons | Built (#75) |
| P0 | Claiming hexagons inside closed loops | Built |
| P0 | Claiming hexagons the route passes through | To build |
| P0 | Hexagons at H3 resolution 11 | To change (resolution 10 today) |
| P0 | Map loads only the hexagons in view, with coarser hexagons as you zoom out | To build |
| P0 | Ownership by run time, most recent wins | To build |
| P0 | Only runs since joining count | To build |
| P0 | Global and group ownership scopes | To build |
| P0 | Map: Everyone and group views, owner colours, every hexagon in view shown | Partly built (personal map, first 1,000 hexagons only) |
| P0 | Create, join, leave and manage groups (screens) | API built, screens to build |
| P0 | Copyable invite links that bypass the allowlist | To build |
| P0 | Several groups per runner | API built |
| P0 | Territory and Explorer leaderboards, all time, global and per group | To build |
| P0 | In-app lost-hex alerts, one per run, with notification list | To build |
| P0 | Dashboard: weekly stats, streak, latest run | Designed, to build |
| P1 | Tap a hexagon to see owner and date | To build |
| P1 | "Lost recently" indicator on the Map | To build |
| P1 | Duplicate-upload detection by start time | To build |
| P1 | Self-service data export and account deletion | To build |
| P2 | Strava sync (invite-only beta) | — |
| P2 | Privacy zones (required before invite-only beta) | — |
| P2 | Early-access request approval flow (invite-only beta) | — |
| P2 | Garmin and Apple Health sync (public launch) | — |
| P2 | Open sign-up (public launch) | — |
| P2 | Weekly and monthly leaderboards | — |
| P2 | Groups competing as teams | — |
| P2 | Hottest hexes | — |
| P2 | Email or push notifications | — |
| P2 | Invite emails sent by Hexagone, and the phone's share sheet | — |
| P2 | Points, with different values for route and enclosed hexagons | — |
| P2 | Runners deleting their own uploads | — |
| P2 | Detecting cycling and other non-run activities | — |
| P2 | Explore a demo map from the landing page | Designed ("Coming soon") |
| P2 | Native iOS and Android apps | — |

---

## 28. Key Product Hypothesis

> **We believe a group of friends who run separately will run more varied routes and stay more engaged if their runs feed a shared territory game in which ground can be taken and taken back, and rankings reward holding and exploring rather than speed.**

We will know this hypothesis is supported if, over the beta, most of the group:

- Claims new hexagons week after week.
- Takes hexagons from each other, and takes them back.
- Says they chose routes because of Hexagone.

rather than uploading their usual runs and ignoring the map.

---

## 29. Riskiest Assumptions to Validate

1. Runners will keep uploading GPX files by hand until Strava sync arrives.
2. Claiming route hexagons as well as enclosed ones keeps out-and-back runners engaged, without making loops feel pointless.
3. Resolution 11 hexagons (about 29 m edges) feel the right size: small enough that every run claims plenty, large enough that counts stay meaningful and taking ground back doesn't need metre-perfect running.
4. Losing territory motivates rather than discourages.
5. A group of fewer than 10, spread across different places, creates enough overlap for hexagons to change hands. Members who never run near each other may compete only on Explorer.
6. Two leaderboards are understood without explanation.
7. Friends are comfortable with each other seeing hexagons near their homes.
8. "Most recent wins by run time" feels fair, including for late uploads.
9. Counting every hexagon a route crosses, including clips from GPS drift, feels fair rather than generous.

---

## 30. Open Questions

- Do invite links expire, or have a use limit? **Current assumption: no, until an admin resets them.**
- Should a runner be alerted when they lose a hexagon only within a group (for example, a clubmate takes it back while a stranger holds it globally)? **Current assumption: alerts follow global ownership.**
- Should the global map show strangers' display names, or anonymise runners outside your groups?
- Is resolution 11 right for urban and rural runners alike?
- With a group spread across towns and countries, should group maps open on the runner's own area, and is Territory meaningful between members who never overlap?
- How long is "lost recently": 7 days?
- When the invite-only beta adds strangers, are privacy zones enough, or are group-only maps needed?

---

## 31. Definition of Beta Success

The closed beta is successful if the group isn't just uploading runs but **changing where they run and competing over territory**.

The strongest early signal is a group in which most members repeatedly:

> **run somewhere new → claim → lose → take back**

over several weeks, and talk about it outside the app.

That supports the central product thesis:

> **Runners already record every run. Hexagone makes those runs count for something the group shares, rewarding the effort to go somewhere new and the effort to go back.**

When that happens, the next phase adds more groups and Strava sync, under its own PRD.

---

## 32. Decision Log

| Date | Decision | Where it is applied |
| --- | --- | --- |
| 2026-11-13 | Primary user for now is a friends group or small running club; individual, competitive and exploration-minded runners are later audiences | §1, §5 |
| 2026-11-14 | Beta runners live in different places, not one area | §1, §5, §25, §29 |
| 2026-11-13 | Closed beta with one group of fewer than 10 runners; invite-only beta and public launch each get their own PRD | §1, §8 |
| 2026-11-13 | Launch markets are the United Kingdom and Canada | §1, §21 |
| 2026-11-13 | Mobile-first web app; native apps later | §1, §7.6, §20 |
| 2026-11-13 | GPX upload only in the beta; Strava sync next, then Garmin and Apple Health | §4, §8, §27 |
| 2026-11-13 | Most recent claim wins, timed by when the run happened | §7.3, §18, BR-02 |
| 2026-11-13 | Only runs completed after the runner joined claim hexagons | BR-04, User Story 2.2 |
| 2026-11-13 | Ownership is calculated globally and separately for each group | §18, BR-03, User Story 3.3 |
| 2026-11-13 | Two all-time leaderboards: Territory (held now) and Explorer (ever claimed) | Epic 6, BR-08 |
| 2026-11-13 | Group screens, leaderboards, lost-hex alerts and the dashboard are all P0 | §27 |
| 2026-11-13 | Lost-hex alerts are in-app only, one per run | Epic 7, §22 |
| 2026-11-13 | Groups are joined by invite link, which bypasses the email allowlist | User Story 1.2, BR-09 |
| 2026-11-14 | Invite links are copied and sent by members; no invite emails or share sheet in the beta | User Story 5.2, §27 |
| 2026-11-14 | A run claims the hexagons its route passes through as well as those inside closed loops; both count equally | BR-01, Epic 3 |
| 2026-11-14 | No points in the beta; may be added in a later iteration | BR-08, §27 |
| 2026-11-14 | The upload size cap is a technical safeguard, not a product limit | User Story 2.1 |
| 2026-11-14 | Runners choose a display name on first sign-in and can change it | User Story 1.3, BR-11 |
| 2026-11-14 | A route claims every hexagon it crosses, even briefly; GPS drift is accepted | BR-01 |
| 2026-11-14 | Runners can't delete uploads in the beta; mistakes are removed by hand | User Story 2.3, BR-13 |
| 2026-11-14 | Runs only, on the honour system; no activity check | User Story 2.1, BR-12 |
| 2026-11-14 | A run starting within a minute of an earlier upload is a duplicate | User Story 2.1, BR-05 |
| 2026-11-14 | Hexagons are H3 resolution 12 (about 10 m edges), up from 10. Superseded the same day | BR-01, §27 |
| 2026-11-14 | Hexagons are H3 resolution 11 (about 29 m edges) instead: it follows the route closely, keeps counts meaningful and blurs exact positions; chosen after comparing one run at 10, 11 and 12 | BR-01, BR-14, §21, §27 |
| 2026-11-14 | The map draws coarser hexagons as you zoom out, coloured by an owner of more than half or shown as Contested; display only | User Story 4.3, BR-14 |
| 2026-11-13 | Runners can belong to several groups; the creator is admin and can make others admin | Epic 5, BR-06 |
| 2026-11-13 | No privacy zones in the beta; required before the invite-only beta | §4, §21 |
| 2026-11-13 | Beta success is changed routes and live competition | §25, §31 |

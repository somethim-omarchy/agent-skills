# Plans contract

Plans live in `plans/` at the repository root, one task per file, like git issues.

- `plans/README.md`: the index.
- `plans/NNN-<task-slug>.md`: one plan per file. `NNN` is the next free three-digit number. The slug is 2–6 kebab-case words naming the task (`014-google-sso-login.md`). Never renumber or rename a plan file after creation; if the title changes, edit only the heading.

Links use repository-root paths with a leading slash, so they work the same from every file: [`app/routes.ts:42`](/app/routes.ts#L42). Name the important symbol after each link. Link plans to each other the same way: [014](/plans/014-google-sso-login.md).

Plan files are shared state. The user may edit them between ticks, especially to answer queued questions. Re-read before editing, merge their edits, and never overwrite them.

## Types

- **Task:** one independently reviewable and shippable deliverable. A request that is a single deliverable produces one task file, which then also carries the request-level sections (Discovery Progress, Outcome, Requirements, Decisions).
- **Epic:** a request that splits into several tasks. The epic file keeps the request-level sections and a task table. Each child task file holds its own steps and estimate, and points back with `Parent`.

## plans/README.md

~~~markdown
# Plans

| # | Title | Type | Status | Parent | Depends on | Estimate | Updated |
|---|---|---|---|---|---|---|---|
| [014](/plans/014-google-sso-login.md) | Google SSO login | Epic | Ready | | | 3–5 d | 2026-09-11 |
| [015](/plans/015-google-oauth-backend-flow.md) | Google OAuth backend flow | Task | Ready | 014 | | 1.5–2.5 d | 2026-09-11 |
| [016](/plans/016-sso-login-button-and-linking.md) | SSO login button and account linking | Task | Ready | 014 | 015 | 1–2 d | 2026-09-11 |
~~~

Order: by number. The index is the only place that lists every plan; keep it in sync with the files.

## Plan file header (every file)

~~~markdown
# 014 — <outcome-oriented task title>

- Type: Task | Epic
- State: Draft — discovery | Awaiting answers | Awaiting confirmation | Ready | Needs decision | Blocked | Done | Dropped
- Request: the user's request as given (epic, or a task that is not part of an epic)
- Parent: 014 (child tasks only)
- Depends on: 015, 017, or `none`
- Prepared against: commit or `working tree`, with date
- Estimate: likely effort range (`TBD` until finalized)
- Confidence: High | Medium | Low
~~~

`Done` and `Dropped` are for later bookkeeping: `implement-plan` (or a pipeline coordinator) sets `Done` after the task's branch is merged, and the user sets `Dropped`. `discover-and-plan` never sets either.

## Request-level sections (epic, or a task that carries its own request)

~~~markdown
## Discovery Progress

- Phase: Research | Interview | Confirm | Finalize | Done
- Ticks: <n>; last tick <date> — one-line summary
- Consecutive waiting ticks: <n>
- Requirements confirmed: no | <date>, with corrections noted

### Research Ledger

| ID | Area | Status | Key facts (linked) |
|---|---|---|---|
| R-01 | Existing auth flow | Done | session login in [`src/auth/login.ts:30`](/src/auth/login.ts#L30) `login` |

### Question Queue

Answer any `pending` question by replying in chat, or by writing in the Answer column.

| ID | Question | Why it matters (task / estimate affected) | Options (recommended first) | Status | Answer | Date |
|---|---|---|---|---|---|---|
| Q-01 | Which identity providers at launch? | shapes 015, ±2 days | Google only (recommended: existing OAuth client); Google + Microsoft; generic OIDC | pending | | 2026-09-11 |

Statuses: pending | answered | delegated (agent chose; also recorded as an assumption) | withdrawn.

## Outcome

The user or customer problem, the desired observable result, and why it matters.

## Project Context

Relevant existing architecture and behavior with linked files and symbols. Include project intent or constraints from relevant Markdown documentation, noting any material conflict with current code. Identify reusable patterns, platform constraints, and boundaries.

### Change Surface

Components the change touches, with their callers and dependents (including indirect wiring), persisted or serialized shapes, and the tests covering them. This drives task boundaries and the estimate.

## Confirmed Requirements

- Functional behavior
- User roles and permissions
- Important states, edge cases, and error behavior
- Compatibility, rollout, or operational constraints

## Non-Goals

Tempting adjacent work that is explicitly outside this plan.

## Acceptance Criteria

Independently verifiable outcomes. Cover the main path, important failure paths, authorization/data boundaries, and applicable accessibility or performance expectations. In an epic, these are the overall criteria; each task carries its slice.

## Technical Approach

The proposed design, affected components, data flow, and why it fits existing project patterns. Call out schema/API contracts, migrations, integrations, and backwards compatibility where applicable.

## Tasks

Epic only.

| # | Task | Depends on | Estimate |
|---|---|---|---|
| [015](/plans/015-google-oauth-backend-flow.md) | Google OAuth backend flow | none | 1.5–2.5 d |

## Rollout and Recovery

Feature flags, staged rollout, migration ordering, monitoring, rollback, and data recovery when the risk warrants it. Otherwise state why no special rollout is needed.

## Estimate

| Task or phase | Likely effort | Range driver |
|---|---:|---|
| ... | ... | ... |
| **Total** | **...** | |

- Basis: team/engineer assumptions, reuse assumptions, and whether tasks overlap
- Included: implementation, tests, review/fixes, migration/docs/rollout as applicable
- Excluded: explicit out-of-scope work
- Confidence: High | Medium | Low, with reason
- Wider contingency range: include when meaningful

## Risks and Mitigations

| Risk | Likelihood / impact | Mitigation or early validation |
|---|---|---|

## Decisions and Assumptions

### Confirmed decisions

Decisions from the interview, with the question ID and brief rationale when useful.

### Assumptions

Agent-selected or unverified premises that affect the plan or estimate, including delegated questions.

### Open questions

Only unresolved questions. Mark each `blocking` or `non-blocking`, name its owner when known, and state which task or estimate it affects.
~~~

## Task-level sections (every task file)

~~~markdown
## Goal

One or two sentences: the deliverable and how it serves the parent outcome.

## Acceptance Criteria

This task's independently verifiable outcomes.

## Implementation Steps

### 1. <Deliverable, not activity>

- Locations: linked files and named symbols; mark genuinely new files as `new`
- Changes: concrete behavior and interfaces to add or alter
- Callers affected: existing callers and dependents that must keep working or be updated
- Dependencies: preceding steps, other plans, external systems, decisions, or migrations
- Verification: targeted tests/checks and expected evidence
- Done when: step-level observable completion condition

Repeat in dependency order. Keep steps independently reviewable where practical.

## Test and Validation Strategy

Unit, integration, end-to-end/manual, migration, regression, security, performance, and observability checks, only where relevant. Include discovered repository-native commands.

## Estimate

Likely range, range drivers, and confidence for this task alone.

## Notes

Task-specific risks, assumptions, and open questions (or links to the parent's).

## Implementation record

Owned by implement-plan (or a pipeline worker); empty until implementation starts.

- Worktree / branch: `.claude/worktrees/NNN-<slug>` / `task/NNN-<slug>`, base <sha>
- Baseline: what was captured before the first edit, and where
- Steps: k/n done, with each step's "Done when" result
- Deviations and questions: anything the plan did not cover, with evidence (a blocking question sets State: Blocked)
- Gate: each verification item → pass / not run (reason, substitute) / fail; CI-equivalent commands; log path
- Commit and merge: <sha>, merged into <branch> at <sha> (or "Ready to merge", with the reason it was not merged)
~~~

## State rules

- `Draft — discovery`: research or interview in progress; later sections may be `TBD`.
- `Awaiting answers`: progress is blocked only by `pending` questions.
- `Awaiting confirmation`: the requirements summary and task breakdown were presented but not yet confirmed.
- `Ready`: requirements confirmed, every section complete, no `blocking` open questions, and every child task `Ready`. The Discovery Progress section may be collapsed to its summary lines.
- `Needs decision`: finalized, but a `blocking` open question remains that the user chose to defer.
- `Blocked`: cannot continue, for example because there is no stated request or an overlap decision is pending.

## Quality bar

A later implementation agent must be able to pick any single task file and determine:

1. what outcome is expected, and what is outside scope;
2. which existing files, symbols, callers, and patterns establish its change surface;
3. what to implement, in what order, and which other plans it depends on;
4. how the task, and the whole request, will be verified;
5. which decisions are confirmed versus assumed;
6. why the estimate has its stated range and confidence.

Avoid vague steps such as "build the backend" or "update the UI". Do not include speculative files merely to make the plan look complete.

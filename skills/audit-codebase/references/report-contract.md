# Audit directory contract

The audit lives in `audit/` at the repository root, split so that each file stays small enough to read in one pass:

| File | Role | Size guide |
|---|---|---|
| `audit/REPORT.md` | Index: progress ledger, conventions, metadata, issue index, coverage. Read at the start of every tick. | under ~15 KB |
| `audit/map.md` | Inventory, memory map, attack surface, caller index, critical flows, sink census, source-to-sink traces, cross-cutting patterns | compact rows; split a section into `audit/map-<section>.md` if the file passes ~60 KB |
| `audit/log.md` | Validation log: every command and check, append-only | one row per check |
| `audit/issues/F-NNN-<slug>.md` | One file per issue, like a git issue | typically under ~8 KB |

These files are shared state. The audit skill and the fix skill may edit them in the same period, in separate loops. Re-read a file immediately before each edit, change only what you own or are updating, and keep entries compact.

## Identity and link rules

- **Issue IDs:** `F-NNN`, one namespace for every lead and finding. The `Status` field, not the prefix, says whether an issue is a candidate or a validated finding. Before assigning the first ID in a repository, look for earlier audits: `git log --all --oneline -- REPORT.md audit/`, and docs citing IDs such as `F-012`. Reuse an earlier ID when the root cause is the same, and otherwise continue numbering after the highest ID ever used, so references in docs and commits stay unambiguous. Never renumber or reuse an ID for a different root cause.
- **Issue filenames:** `audit/issues/F-NNN-<slug>.md`, where the slug is 2–6 kebab-case words naming the problem (`F-027-social-callback-trusts-account-id.md`). Never rename a file after creation, even if the title changes, so links stay stable.
- **Other IDs:** memory IDs by role (`MOD-...`, `ENTRY-...`, `DATA-...`, `CFG-...`, `TEST-...`, `EXT-...`); traces `T-NNN`; work items `P0`–`P8` for single-row passes, `U-<name>` for review units, `S-<class>` for sink-census rows, and descriptive IDs such as `V-early-1` for verification batches.
- **Links:** repository-root paths with a leading slash, the same from every file: [`apps/api/users.ts:42`](/apps/api/users.ts#L42), [F-027](/audit/issues/F-027-social-callback-trusts-account-id.md). For a symbol spanning lines, link the defining line and name the symbol. Add a plain locator after fragile or generated locations: `apps/api/users.ts:42 — UserService.update`. Locators let a later agent re-find a symbol after line numbers drift.
- **Edges:** `SOURCE_ID --relationship--> TARGET_ID` with evidence links. Useful relationships: `imports`, `calls`, `calls-indirectly` (state the mechanism), `implements`, `constructs`, `reads`, `writes`, `routes-to`, `emits`/`handles`, `configured-by`, `persists-to`, `guarded-by`, `tested-by`.
- Never link to a directory when a specific file or symbol proves the claim.

## Issue lifecycle and ownership

| Status | Meaning | Set by |
|---|---|---|
| `Candidate` | Unvalidated lead. Never act on it as a finding. | audit |
| `Open` | Validated finding with a proposed fix | audit (promotion) |
| `Rejected (reason)` | Lead disproven; kept so it is not raised again | audit |
| `Superseded by F-NNN` | Merged into another issue with the same root cause | audit or fix |
| `In progress` | Claimed by the fixer; Fix notes hold the recovery point. A fix waiting for the coordinator's merge stays `In progress`, with a `Ready to merge: <branch> @ <sha>` line in Fix notes | fix |
| `Blocked (question)` | The fix needs the user | fix |
| `Resolved` | Fixed and verified, or found already fixed | fix, or audit in watch mode for `Open` issues |

| Content | Audit | Fix |
|---|---|---|
| `REPORT.md` progress ledger, conventions, coverage | writes | never |
| `REPORT.md` issue index | adds rows, updates titles and severity | updates the Status column for its transitions |
| `map.md` | writes | refreshes links and trace verdicts touched by a fix |
| `log.md` | appends | appends |
| Issue file: body sections | writes | updates evidence and scope discovered during a fix |
| Issue file: `Status` from `Open` onward, `Fix notes`, `Resolution` | never (except watch-mode resolution of `Open`) | owns |

## audit/REPORT.md

~~~markdown
# Codebase Audit Report

## Audit Progress

- State: In progress | Complete | Watching | Blocked (reason)
- Run: <n> (started <date>; `--restart` yes/no)
- Scope: roots audited (from arguments or the whole repository)
- Audited revision: <commit> + working-tree changes yes/no
- Ticks: <n>; last tick <date> — one-line summary
- Next: <item ID> — <target>

| Item | Pass | Target | Status | Revision | Date | Note |
|---|---|---|---|---|---|---|
| P0 | Setup | repository | Done | a1b2c3d | 2026-09-11 | |
| U-auth | Unit review | `src/auth/**` (~1,300 LOC) | In progress | a1b2c3d | 2026-09-11 | session.ts done; resume at token.ts |
| V-early-1 | Verification | F-031, F-034 (likely High) | Pending | | | |

Item statuses: Pending | In progress | Done | Stale | Skipped (reason). Work runs in table order; insert a row earlier to run it earlier. Done-row notes: one short sentence at most (details belong in `log.md`).

### Conventions

Standing rules for this audit that every tick must honor: user decisions (accepted risks, priorities, exclusions) and any process rules set for this run. One line each, with date.

## Audit Metadata

- Audited revision: commit, with date
- Scope: reviewed roots and important exclusions
- Stack: languages, frameworks, package/build tools, static tools available
- Existing worktree changes: concise list or `none`
- Earlier audits: where found, highest ID used, how IDs were reconciled

## Issues

Counts: open N (Critical a, High b, Medium c, Low d) · candidates N · in progress N · blocked N · resolved N · rejected N · superseded N (only when non-zero)

| ID | Title | Status | Severity | Confidence | Category | Updated |
|---|---|---|---|---|---|---|
| [F-027](/audit/issues/F-027-social-callback-trusts-account-id.md) | Social callback trusts the browser-supplied account ID | Open | High | High | Security | 2026-09-11 |

Order: Open and In progress by severity, then Blocked, then Candidate, then closed statuses.

The index is generated from the issue files' headers by `scripts/audit_index.py rebuild`. Edit the issue files, then rebuild; do not hand-edit rows. `scripts/audit_index.py check` validates headers, statuses, the index, the counts line, and every link and line anchor. Link drift in closed issues is only a warning, because their evidence describes the revision they were closed at.

## Coverage and Limitations

Updated every tick.

- Reviewed in depth: units and passes done
- Pending: what remains in the queue
- Sampled or excluded: and why
- Sink census completeness and unresolved dynamic edges
- Runtime, environment, fixture, or tool limitations
- Overall confidence (final at P8)
~~~

## audit/map.md

~~~markdown
# Codebase Map

## Project Inventory

```text
repository/
├── ...
└── ...
```

Short note on entry points and generated/vendor boundaries.

## Components

| ID | Location / symbols | Responsibility | Key relationships | Issues |
|---|---|---|---|---|
| ENTRY-API | [`src/server.ts:20`](/src/server.ts#L20) — `start` | Starts HTTP service | calls MOD-ROUTER; configured-by CFG-ENV | F-002 |

## Relationship Tree

```text
ENTRY-API src/server.ts::start
└─ calls → MOD-ROUTER src/router.ts::router
   ├─ reads → DATA-USERS src/store.ts::UserStore
   └─ tested-by → TEST-ROUTER test/router.test.ts
```

## Attack Surface and Trust Boundaries

| Entry | Kind | Location | Untrusted inputs | Authn | Authz / scoping | Reaches |
|---|---|---|---|---|---|---|
| ENTRY-API-USERS | HTTP `PATCH /users/:id` | [`src/routes/users.ts:31`](/src/routes/users.ts#L31) | `:id`, JSON body | session middleware | none on object ⚠ | MOD-USERS, DATA-USERS |

Then a short list of trust boundaries and where each is enforced, and the authorization matrix (P5).

## Caller Index

Only for security-relevant, contract-heavy, or issue-relevant symbols.

| Symbol | Defined | Callers (all, linked) | Contract the callers must satisfy | Violations |
|---|---|---|---|---|
| `runQuery(sql, params)` | [`src/db.ts:12`](/src/db.ts#L12) | 9 direct, 2 via `repo.raw` | `sql` constant; values only in `params` | [`src/report.ts:88`](/src/report.ts#L88) → F-004 |

State unresolved dynamic edges explicitly.

## Critical Flows

Important request, command, job, state, or data flows in execution order. Link every hop; note trust boundaries, side effects, ownership, and error propagation.

## Sink Census

| Row | Sink class | APIs and wrappers searched | Found | Traced | Safe | Issues | Excluded (reason) |
|---|---|---|---|---|---|---|---|
| S-sql | SQL/ORM raw | `query(`, `raw(`, `db.exec` | 23 | 23 | 20 | F-003, F-004 | 1 (test fixture) |

## State Census

One row per implicit or explicit state machine (playbook §11): DB status columns, stateful structs and flag sets, and frontend flows.

| Row | Machine | States (declared / written / read) | Writers (linked, from → to, guard) | Terminal | Exit from each non-terminal | Companions | Checked | Issues |
|---|---|---|---|---|---|---|---|---|
| M-posts | `posts.status` | 8 / 8 / 8 | 14 writers; [`jobs/workflows.go:780`](/jobs/workflows.go#L780) any → published, unguarded | published | publishing: job finalizer, no reaper | `failed`, `published_at` | T-031 | F-040 |

## Source-to-Sink Traces

Safe traces take one line:

- T-007 — Safe: `GET /search` `q` → [`src/search.ts:40`](/src/search.ts#L40) → parameterized [`src/db.ts:12`](/src/db.ts#L12) — guard: bound parameter.

Traces behind an issue take a short block (source, path with every hop linked, guards seen, revision), and the issue file links to them.

## Cross-Cutting Patterns

Repeated symptoms that do not merit separate issues, pointing to the owning issue IDs.
~~~

## audit/log.md

~~~markdown
# Validation Log

| Date | Item | Command/check | Result | Interpretation |
|---|---|---|---|---|
| 2026-09-11 | P0 | `git rev-parse HEAD`; `git status --short` | `a1b2c3d`; clean | baseline |
~~~

Append-only. Record exact commands, outcomes, and limitations. Never print secret values.

## audit/issues/F-NNN-slug.md

A candidate needs only the header, Summary, Evidence so far, and Confirm or refute by. A rejected or superseded issue keeps its header, Summary, and a Closure section of one to three lines. A validated finding (`Open` onward) has every section.

~~~markdown
# F-027 — Social callback trusts the browser-supplied account ID

- Status: Candidate | Open | In progress | Blocked (question) | Resolved | Rejected (reason) | Superseded by F-NNN
- Severity: Critical | High | Medium | Low  (for candidates: "likely High"; for closed leads: "n/a")
- Confidence: Confirmed | High | Moderate  (for candidates: Suspected; "Likely" is a legacy synonym of High)
- Category: Security | Correctness | Concurrency | Data integrity | Performance | Duplication | Maintainability | Testing | Configuration
- Map IDs: MOD-X, ENTRY-Y; traces T-003
- Raised: 2026-09-11 in U-auth-integrations at a1b2c3d · Aliases: C-027 (earlier IDs, if any)
- Updated: 2026-09-11

## Summary

One or two sentences: what is wrong and why it matters.

## Evidence

Precise linked definitions and use sites. (Candidates: "Evidence so far".)

## Confirm or refute by

Candidates only: the checks that would settle it.

## Trigger and path

How execution reaches the problem, from which entry point, with every hop linked or a link to the trace.

## Preconditions

Attacker capability, role, configuration, or timing required.

## Impact

Concrete outcome and affected users or systems.

## Analysis

Why it is faulty.

## Disproof attempts

Guards, framework behavior, types, constraints, and tests checked, and why each fails to prevent the issue. The strongest counterargument and why it fails.

## Variants

Pattern searched, count found, and every linked instance included in this issue.

## Blast radius

Callers, contracts, persisted shapes, and tests that a fix will touch.

## Proposed fix

A design, not a patch:

- Choke point: the layer every vulnerable path passes through that owns the invariant
- Changes: files and symbols to change, and how their behavior changes
- Callers to update: each affected caller and how it must handle the new behavior
- Invariant: what must hold on every path after the fix
- Tests: the regression test, and negative tests for the relevant bypass classes
- Compatibility and migration: data, API, and rollout concerns
- Alternatives considered: and why this one is preferred
- Effort and risk: rough size and what could go wrong

## Verification

Observations and checks that would prove the eventual fix, including bypass cases.

## Fix notes

Owned by fix-audit-findings: claim date, baseline revision, dirty files before the claim, intended files, blocked question.

## Resolution

Owned by fix-audit-findings (or audit in watch mode): date, resolving revision or commit, invariant established, code and test links, bypass classes tested, verification commands, limitations.

## Closure

Rejected or superseded issues only: the reason, with evidence links.
~~~

## Severity calibration

- **Critical:** readily exploitable compromise, irreversible widespread data loss, or total failure of a critical system.
- **High:** likely serious correctness/security failure, major data integrity issue, or outage on a realistic path.
- **Medium:** meaningful bounded defect, recurring operational problem, or costly structural risk with a plausible path.
- **Low:** localized reliability or maintainability defect with specific evidence and limited current impact.

Use the highest severity justified by demonstrated reachability and impact, not by the smell category alone. Lower severity when exploitation requires an already-privileged actor, and state that precondition.

## Confidence calibration

- **Confirmed:** reproduced, or a complete linked path with no guard, and disproof attempts documented.
- **High:** complete static path; one runtime fact (configuration, deployment, third-party behavior) is assumed and named.
- **Moderate:** plausible path with a named gap in the evidence; say what would settle it.

A lead weaker than Moderate stays a candidate.

## Map quality bar

The map and issue files must let a later agent answer, without rescanning the whole repository:

1. Where does execution enter this area, and what untrusted input arrives there?
2. Which symbols own the behavior and data?
3. What calls or configures them, including indirect dispatch?
4. What contracts must callers satisfy, and where are they violated?
5. What side effects and external boundaries occur?
6. Which tests exercise them?
7. Which issues touch them, and what else will change in a fix?

Keep the map compact: architectural, security-relevant, and issue-relevant nodes only, not every file or symbol.

---
name: audit-codebase
description: Rigorously audit a local codebase without changing its implementation. Map files, symbols, call relationships, entry points, and trust boundaries; trace where and how code is called and how untrusted data reaches dangerous sinks; find vulnerabilities, defects, duplication, dead or suspicious code, performance risks, and maintainability smells. Each issue gets its own file under audit/issues/ (like a git issue, with evidence and a proposed fix), indexed by audit/REPORT.md, for a later fixing pass. Runs in resumable, bounded ticks, so it works under /loop (fixed interval or self-paced) or standalone, and can keep watching new commits. Use for repository audits, security reviews, vulnerability hunts, code-health reviews, technical-debt inventories, architecture mapping, or requests to inspect a project and record actionable findings, including "keep auditing in a loop".
argument-hint: "[scope-path ...] [--watch] [--restart] [--tick] [--classic]"
---

# Audit Codebase

Audit the repository and write only inside the `audit/` directory at its root. Do not fix source code, configuration, tests, or dependencies. The directory is both the deliverable and the audit's persistent state:

- `audit/REPORT.md`: the index. It holds the progress ledger, standing conventions, metadata, the issue index, and coverage. It is kept small because every tick reads it first.
- `audit/map.md`: inventory, memory map, attack surface, caller index, critical flows, sink census, source-to-sink traces, and cross-cutting patterns.
- `audit/log.md`: every command and check, append-only.
- `audit/issues/F-NNN-<slug>.md`: one file per issue, like a git issue. An issue starts as a `Candidate` lead, is validated to `Open` with a proposed fix, and is closed as `Resolved`, `Rejected`, or `Superseded`.

Follow `references/report-contract.md` for the schema, ID rules, and link format. Use `references/analysis-playbook.md` for analysis techniques and catalogs. Use `${CLAUDE_SKILL_DIR}/../fix-audit-findings/references/fix-playbook.md` (normally `~/.claude/skills/fix-audit-findings/references/fix-playbook.md`) for correct fix patterns when writing proposed fixes.

Invocation arguments (may be empty): $ARGUMENTS

- Scope paths: restrict the audit to these roots. Record them in the ledger; if they differ from the recorded scope, re-plan the work queue for the new scope and keep existing issues.
- `--watch`: after the audit completes, keep re-auditing code that changes instead of ending the loop.
- `--restart`: start a new full run: rebuild the ledger and rerun every pass, re-verifying existing issues instead of duplicating them. Keep every issue, trace, and memory-map ID. It takes effect once. If the current run was already started by `--restart`, continue that run instead, because under `/loop` the same arguments repeat on every tick.
- `--classic`: use the tick-by-tick unit review and verification instead of the deep scan workflow.
- `--tick`: force loop-mode behavior (one bounded tick) even when not started by `/loop`.

Typical use: `/loop /audit-codebase` (self-paced until complete), `/loop 20m /audit-codebase --watch` (keep auditing new commits), or `/audit-codebase` (run to completion in one session).

## Execution model: ticks

The audit advances in ticks. A tick loads state from disk, completes one bounded slice of the work queue, persists it under `audit/`, and reports status.

- **Loop mode**: this invocation was started by `/loop` (its instructions are in the current turn), by a scheduled-task or wakeup fire, or with `--tick`. Run exactly one tick, then end with the status block.
- **Standalone**: run ticks back-to-back until the ledger reaches `Complete` or `Blocked`. Persist after every tick so an interruption or context compaction loses at most one tick.

Disk is the source of truth. At the start of every tick, re-read `audit/REPORT.md` and the current git state. Do not rely on conversation memory from earlier ticks. It may have been compacted, and the user or another session (for example a `fix-audit-findings` loop) may have changed the issues or the code since.

### Tick procedure

1. **Load state.** Resolve the repository root with `git rev-parse --show-toplevel` when available; otherwise use the working directory. Read `audit/REPORT.md`, starting with Audit Progress and Conventions, and honor every convention. Then read only what the chosen item needs: the unit's rows in `map.md` and the related issue files. If `audit/` does not exist, the next item is `P0`. Apply `--restart` as described under the arguments.
2. **Check freshness.** Record `git rev-parse HEAD` and `git status --short`. For every `Done` item, check whether its files changed since its recorded revision (`git diff --name-only <revision> -- <paths>`, plus uncommitted changes). Mark changed items `Stale`, along with every trace whose hops touch changed files.
3. **Choose work.** Pick an `In progress` item first (resume an interrupted tick from its note), then `Stale` items, then `Pending` items in table order. Take as many items as fit the tick budget. Stop at an item boundary, never mid-item.
4. **Do the work** as described under Passes.
5. **Persist.** Write or update the issue files, then `map.md`, then append to `log.md`. Finally update `REPORT.md`: ledger rows, issue index, counts, tick counter, last-tick summary, and Coverage. Re-read each file right before editing it and apply targeted edits. If an edit fails because the file changed, re-read and reapply.

   The issue index is derived from the issue files' headers. Regenerate it with `python3 ${CLAUDE_SKILL_DIR}/scripts/audit_index.py rebuild` rather than editing rows by hand. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/audit_index.py check` before finishing P8, and whenever links may have drifted. It checks headers and statuses, index-to-file agreement, the counts line, and that every link and line anchor resolves.
6. **Report** with the status block.

Tick budget: one unit of deep review (roughly one module or feature slice, up to about 2,000 lines of first-party code; split larger units during P1), or one cross-cutting pass, or a batch of 5–10 issue verifications. Finish one item thoroughly rather than touching many shallowly. An item that cannot finish stays `In progress`, with a note stating exactly where to resume.

Keep the index small. Done-row notes are one short sentence at most; details belong in `log.md` and the issue files. Issue-index titles are one line.

### Status block and loop control

End every tick with:

```text
AUDIT TICK <n> (run <r>) — <ledger state>
Did: <items completed, with IDs>
Next: <next item ID and target>
Issues: open <counts by severity>; candidates <k>; resolved <r>
Loop: continue | done | watching | blocked
Noop: true | false
```

Only control the loop when the `/loop` input invokes this skill directly. When a pipeline or another caller invoked it, report the verdict and leave loop control to the caller.

Map the verdict to loop control:

- `continue`: queue items remain. Under self-paced `/loop`, reschedule soon (60–120 s); the work is local and there is nothing to wait for.
- `done`: every pass is complete and `--watch` is absent. End the loop. Self-paced: call `ScheduleWakeup` with `stop: true`. Fixed interval: load `CronList` and `CronDelete` via ToolSearch (`select:CronList,CronDelete`), find the job whose prompt invokes this skill, and delete it. Do not call `ScheduleWakeup` from a fixed-interval cron tick.
- `watching`: complete, with `--watch`. The next tick checks for code changes. Report `Noop: true` when nothing changed. Self-paced heartbeat: 1200–1800 s.
- `blocked`: progress needs the user (for example ambiguous scope, or conflicting manual edits to the audit files). End the loop as for `done`, and state the question.

`Noop` is `false` whenever the tick changed any file under `audit/`.

## Deep scan mode (default)

When the Workflow tool is available, run unit review (P4) and verification (P7) as one multi-agent deep scan instead of tick-by-tick reading. It works like CodeRabbit or Alibaba's open-code-review: related files are reviewed in bundles by isolated reviewers against a fixed checklist, then separate skeptics try to refute every finding, and only survivors are reported. Invoking this skill counts as the user's opt-in to that workflow. Use the classic tick procedure only with `--classic`, when the Workflow tool is missing, or for `--watch` ticks on a few changed files.

1. **Bundle (P1).** Size every first-party source directory (non-test, non-generated lines). Cut bundles of about 5–12k lines along package or feature boundaries, so that every source file is in exactly one bundle. Split big packages by file name or subfolder, and gather small packages into alphabetical catch-all bundles. Add bundles for SQL migrations/queries and for deploy/infra scripts. Record the bundle list in `map.md` as the `U-*` units.
2. **Run** `${CLAUDE_SKILL_DIR}/references/deep-scan.workflow.js`. It takes `root`, `bundles`, `known` (every Open/Candidate issue, so reviewers look for new ones and every known issue is re-checked against the current code), `rules` (the repository's read-only and heavy-job rules) and `load`. Large inputs go into a run copy of the script under the scratchpad, with the data put in place of `args`, and the copy is started with `scriptPath`. Inline args would flood the context.
3. **Completeness.** The run reports `failedBundles` and `incomplete` (agents that died, for example on network errors). Resume with `resumeFromRunId` until both are empty. A scan with an unreviewed bundle or an unverified finding is not complete.
4. **File (P7).** Write each surviving finding (`holds: true`) as an `Open` issue in `audit/issues/` with the skeptics' reasons under Disproof attempts. Write each refuted finding as `Rejected` with the reasons, and close each re-checked issue that no longer holds as `Resolved` or `Rejected`. Then rebuild the index with `scripts/audit_index.py rebuild`.
5. **Second pass on request.** A "do another pass" reruns the same script with a fresh `known` list. That re-checks every existing issue with new skeptics and reviews every bundle again.

Severity: two skeptics must both fail to refute a must-fix (High/Critical) finding; one is enough for the rest.

## Passes

Plan the work queue during P0 and P1 as ledger rows. Each row is one tick-sized item.

| Pass | Items | Output |
|---|---|---|
| P0 Setup | one | metadata, scope, stack, commands, earlier audits, migration of a legacy report |
| P1 Inventory and map | one or two | inventory, components, relationship skeleton, unit list `U-*` |
| P2 Attack surface | one | entry points, untrusted inputs, trust boundaries, authn/authz per entry |
| P3 Sink census | one per few sink classes, plus `S-state` | every dangerous sink located and counted; every implicit state machine listed |
| P4 Unit review | one per `U-*` | deep per-unit analysis, caller index, candidate issues |
| P5 Flow tracing | one per entry group or sink class | forward and backward traces `T-*`, authorization matrix |
| P6 Cross-cutting | one per theme | duplication, configuration, dependencies, concurrency, tests, dead code |
| P7 Verification | batches of candidates | candidates promoted to `Open` with a proposed fix, or rejected |
| P8 Finalize | one | reconciled audit, link and line checks, coverage statement |

A later pass can add rows to an earlier one, for example a newly discovered entry point or unit. Candidates raised after the last P7 row get new verification rows before P8 can finish.

**Serious leads are verified early.** When a candidate is rated likely High or Critical, insert a verification row (`V-early-N`) directly after the current item, so it is verified on the next tick rather than at P7. This lets a `fix-audit-findings` loop start on confirmed findings while the audit continues.

### P0 — Establish scope

1. Read applicable `CLAUDE.md`/`AGENTS.md` files and repository documentation before judging conventions.
2. Inspect `git status --short`. Preserve user changes, and distinguish pre-existing failures from audit findings.
3. Discover files with `rg --files --hidden`, respecting ignore rules. Add targeted checks for important ignored or hidden project metadata. Exclude `.git`, vendored dependencies, generated output, caches, binaries, and large data unless evidence points into them.
4. Detect languages, frameworks, package managers, entry points, build/test commands, generated-code boundaries, and which static tools are already installed.
5. **Find earlier audits.** Run `git log --all --oneline -- REPORT.md audit/`, read the most recent earlier report with `git show <commit>:<path>`, and grep the whole tracked tree for cited audit IDs: docs, code comments, tests, and commit messages (`git grep -n -E 'F-[0-9]{3}'`, `git log --oneline | grep -E 'F-[0-9]{3}'`). Record them under Earlier audits in the metadata. New issues continue numbering after the highest ID cited anywhere. An issue with the same root cause as an earlier one reuses its ID and records the earlier history.
6. **Migrate a legacy single-file report.** If a root `REPORT.md` in the older single-file format exists, split it into the `audit/` layout:
   - ledger and conventions → `REPORT.md`;
   - inventory, map, census, and traces → `map.md`;
   - validation log → `log.md`;
   - each finding or candidate → its own issue file.

   Assign IDs per the contract, and record the old IDs as `Aliases`. Convert links to repository-root form. Verify that nothing was lost (every old ID, row, and evidence link is present), then delete the legacy root file so there is a single source of truth. Record the migration in `log.md`.

### P1 — Inventory and map

In `map.md`, write a compact project tree covering important source, test, configuration, migration, script, and documentation paths. Collapse uninformative directories, and annotate exclusions and generated/vendor boundaries.

Start the memory map: stable component IDs, files, key symbols, responsibilities, and directed edges. Treat it as a durable navigation index for a later fixing agent. Split first-party code into review units `U-*` along module or feature boundaries, sized to the tick budget, and add one P4 row per unit.

### P2 — Attack surface and trust boundaries

Enumerate every way execution enters the system:

- HTTP, RPC, and GraphQL routes;
- websocket and message handlers;
- CLI commands, jobs, and schedulers;
- webhooks, and file and archive parsers;
- IPC and plugin hooks;
- framework lifecycle callbacks and exported library APIs.

For each entry, record the untrusted inputs it accepts, the authentication and authorization applied, and the components it reaches. Use the framework's registration mechanisms (route tables, decorators, DI, conventions), not only filenames. Record trust boundaries: where data crosses from user, network, tenant, or third party into trusted code, and where it leaves.

### P3 — Sink census

For every sink class in the playbook that applies to the stack, search the whole in-scope codebase for all sink APIs and for wrappers around them. Record counts per class in the Sink Census. Enumerate; do not sample. Add P5 rows so every census sink gets a trace or an explicit, reasoned exclusion.

Also take the **state census** (playbook §11) as its own P3 row `S-state`: every status/state/stage column and its CHECK, every writer of each, stateful structs and flag sets in code, and frontend flow state. Record each machine in `map.md` § State Census, and add P5 rows (one per group of related machines) to check them against playbook §11.

### P4 — Unit review

For the unit's files:

1. Read every file in full. Grep excerpts are for discovery, not review.
2. For each externally reachable or security-relevant symbol, find **all** callers. That includes indirect callers: aliases and re-exports, interface and override dispatch, callbacks, registries, decorators, events, reflection, and cross-language wiring (playbook §1). Record unresolved dynamic edges explicitly. Never conclude "no callers" or "dead code" before checking the indirect mechanisms.
3. Check contracts in both directions (playbook §2):
   - What the symbol requires: validated input, authorization, non-null values, lock held, transaction open, normalized path. Verify that every caller guarantees each requirement.
   - What the symbol produces: errors, null or empty returns, exceptions, partial side effects. Verify that every caller handles each one.

   Compare sibling callers. A guard present in most callers but missing in one is a lead.
4. Identify which parameters can carry attacker-influenced data (link to the P2 inputs), and follow them into callees.
5. Review state and side effects: shared mutable state, caches, I/O, transactions, locks, check-then-act sequences, retries and idempotency, and resource lifecycles on error paths.
6. Look for correctness faults, unsafe assumptions, error-path failures, races, leaks, boundary-condition bugs, secret handling, weak interfaces, and misleading names. For example, verify that `sanitize`, `isAdmin`, or `validate` actually does what its name promises, for all inputs.
7. Update `map.md` and the caller index. Record every suspicion as a new issue file with `Status: Candidate`, holding a summary, the evidence so far, and the checks that would confirm or refute it. First check the issue index for an existing issue with the same root cause, and extend that issue instead of opening a duplicate.

### P5 — Flow tracing

- **Forward:** from each entry point, follow each untrusted input hop by hop through every callee to sinks, persistence, and outbound calls. Note validation, authorization, and transformation at each hop.
- **Backward:** from each census sink, walk callers upward until you reach a source or a constant. Record every distinct path, not just the first one found.
- **Guard sufficiency** (playbook §5): a path is safe only when the guard runs on every route to the sink, suits the sink's context, runs after the last decode, normalization, or concatenation, and cannot be bypassed or disabled by configuration.
- **Stored data:** treat data written by users and later read back (database, cache, files, queues) as a source again (second-order flows).
- **Authorization matrix:** for every route or command, tabulate each operation against authentication, role or ownership check, tenant scoping, CSRF, and rate limiting. Differences between siblings, and object lookups not scoped to the owner or tenant, become candidates.

- **State machines:** for each State Census machine, list every writer with its from → to transition and guard, then run the playbook §11 checks: unguarded writers, stuck non-terminal states with no reaper, job and domain rows finishing apart, vocabulary drift, webhook ordering, duplicated derived state, per-iteration leaks, and decisions taken on transitions.

Record every trace as `T-*` in `map.md` with its verdict. Include `Safe` traces, kept to one line with the guard linked, so later ticks and the fixer do not redo them.

### P6 — Cross-cutting

Cover what per-unit review misses:

- copied logic and near-duplicates that drifted apart, and conflicting definitions;
- dead, unreachable, or obsolete code (only after the indirect-caller checks);
- configuration traps and insecure defaults (debug, CORS, cookies, TLS, CSP, permissions);
- dependency risk;
- concurrency across components;
- performance hazards on a plausible hot path;
- missing or misleading tests around concrete risks.
- the easily missed vectors in playbook §12 (denial of wallet, LLM input, fetch-anything features, identity lifecycle, time, money, messaging abuse, OAuth, deploy and schema, resilience, silent failure, soft delete, supply chain, browser surface).

Use repository-native static checks, tests, linters, type checkers, and build commands when they are discoverable, safe, and reasonably bounded. Use installed security analyzers (for example semgrep, bandit, gosec, cargo-audit) only when already present and runnable without writes. Prefer targeted commands before broad expensive ones. Treat tool output as candidates, never as findings without a trace. Record exact commands, outcomes, and limitations in `log.md`.

### P7 — Verification

Promote a candidate to `Open` only after all of the following:

1. Trace the execution or dependency path from a real entry point or trigger, and link every hop.
2. Cite precise lines and symbols plus related callers, tests, schemas, or configuration.
3. Explain the observable failure or maintenance cost and the conditions that trigger it, including attacker capabilities and preconditions.
4. Run the playbook's disproof checklist (§8): compensating guards, framework defaults, types, schemas, database constraints, feature flags, deployment configuration, test evidence, and whether the "attacker" is already privileged. Record the strongest counterargument and why it fails.
5. Separate confirmed defects from risks that need runtime confirmation, and set Confidence accordingly.
6. Run variant analysis (§9): generalize the root cause, search the codebase for other instances, and group one root cause under one issue. Mark merged duplicates `Superseded by F-NNN`.
7. Calibrate severity by demonstrated reachability and impact, not by category.
8. Write the **Proposed fix**: the choke point, changes by file and symbol, the callers to update, the invariant, the regression and bypass tests, compatibility concerns, alternatives, and effort and risk. Base it on the blast radius from the caller index and on the fix playbook. Describe the fix; never write a patch.

For Critical and High candidates, when the Agent tool is available, optionally give a fresh subagent only the claim and its locations, and ask it to refute the claim. Record the outcome under Disproof attempts.

**Parallel verification.** When a verification batch is large (more than about 5 issues) and the Agent tool is available, you may split it across at most 4–5 background verification workers. Brief them from `${CLAUDE_SKILL_DIR}/../pipeline/references/worker-briefs.md`, "Verification worker". Each worker:

- rewrites only its own issue files;
- never edits `REPORT.md`, `map.md`, or `log.md`;
- never creates issue files;
- performs no git writes;
- reports new defects in its final report.

While workers run, ticks only collect finished reports (`Noop: true` when none finished). When a worker finishes, integrate its results yourself: file its new defects as `Candidate` issues, then update the index, ledger row, and log.

Reject a candidate that does not hold with `Status: Rejected (reason)` and a short Closure section, so the same lead is not raised again. Do not report style preferences unless they create a specific, evidenced cost. Do not inflate the audit with speculative, redundant, or tool-only warnings.

### P8 — Finalize

Order the issue index by status and severity. Then verify all of the following:

- every `Open` issue has a complete template, including a Proposed fix;
- the issue index lists every file in `audit/issues/`, and its statuses agree with the files;
- all links resolve and line numbers match the current files;
- every issue appears in the map;
- every census sink has a trace verdict or a reasoned exclusion;
- `git status --short` shows no audit-created change outside `audit/`.

Complete Coverage and Limitations with an honest confidence statement, or a clean-audit statement when no actionable issues were found. Set the ledger state to `Complete`, or to `Watching` with `--watch`.

## Watch mode

With `--watch`, each tick after completion diffs the current tree against the ledger's audited revision. If nothing changed, report `Noop: true`. Otherwise:

- mark the units, traces, and census rows touching changed files as `Stale`, and put changed files that fall outside any unit into a new unit;
- re-verify `Open` issues whose evidence touches changed files. When the trace no longer holds, set the issue to `Resolved` with a Resolution section recording the evidence and revision;
- run the stale items in later ticks as usual, then advance the audited revision.

## Coordination with fix-audit-findings

A fix loop may run at the same time. It owns `Status` from `Open` onward, and the `Fix notes` and `Resolution` sections. Do not change an issue that is `In progress` or `Blocked`, beyond appending evidence. You may create issues, update evidence and proposed fixes on `Open` issues, and resolve `Open` issues in watch mode. Preserve IDs, and record history instead of deleting it.

## Guardrails

Never modify source, configuration, tests, dependencies, or lockfiles. Do not install project dependencies, access production systems, or apply automatic fixes. Never print secret values into the audit; cite their location and type only. The only file this skill may delete is a legacy root `REPORT.md` that it has migrated into `audit/`.

**Probing:** to confirm a finding, you may start disposable local services under the scratchpad (for example an embedded Postgres on a non-default port, a Redis-compatible server, an SMTP sink). You may also migrate scratch databases from the repository, run existing tests, and write probe programs, but only under the scratchpad, never inside the repository. Record every service and probe in `log.md`, reuse services a pipeline already runs, and stop the ones you started when the audit completes. A reproduction raises Confidence to `Confirmed`.

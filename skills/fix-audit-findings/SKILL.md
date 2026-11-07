---
name: fix-audit-findings
description: Implement, test, and document fixes for validated issues recorded by the audit-codebase skill in audit/issues/ (one file per issue, indexed by audit/REPORT.md). By default each issue is fixed in its own git worktree and branch and fast-forward merged after a gate proves the tests actually ran (--no-merge leaves branches for review, --in-place works in the current checkout). It also runs as a background lane worker for the pipeline skill's parallel fixes. Before each fix it re-derives the defect through callers, callees, data flows, and trust boundaries. After each fix it re-traces every path, hunts for bypasses and variants, checks every caller against the changed contract, and proves the fix with regression and negative tests. One issue (or root-cause batch) per resumable tick, so it runs under /loop or standalone. Use when asked to fix, address, resolve, remediate, or work through audited defects or issue IDs such as F-027. For many issues in parallel, prefer /pipeline.
argument-hint: "[F-027 ...] [--no-merge | --in-place [--commit]] [--tick]"
---

# Fix Audit Findings

Treat the audit as a navigation index and persistent ledger, not unquestioned truth. `audit/REPORT.md` indexes the issues, and each issue lives in its own file, `audit/issues/F-NNN-<slug>.md`, with evidence and a proposed fix. For each selected issue:

1. Revalidate it against the current code.
2. Map everything the fix will touch.
3. Implement the smallest complete root-cause fix at the right layer.
4. Try to break the fix.
5. Prove it with tests that actually run.
6. Record the result in the issue file.

Invocation arguments (may be empty): $ARGUMENTS

- Issue IDs (`F-027`, `027`, or `27`): fix only these, in the given order. With none, work through every `Open` issue.
- `--no-merge`: in worktree mode, commit on the task branch and leave it, with its worktree, for the user to review.
- `--in-place`: work in the current checkout, without worktrees. Commit only with `--commit`.
- `--tick`: force loop-mode behavior (one issue per invocation) even when not started by `/loop`.

Typical use: `/loop /fix-audit-findings` (one issue per tick until none remain), `/fix-audit-findings F-027`, or `/fix-audit-findings F-027 --no-merge`. To fix many issues in parallel lanes, use `/loop /pipeline fix the open audit issues`; it runs this skill in worker mode.

Reference material:

- Audit layout, issue template, lifecycle, and ownership: `${CLAUDE_SKILL_DIR}/../audit-codebase/references/report-contract.md`.
- Caller discovery, contracts, sources and sinks, and guard sufficiency: `${CLAUDE_SKILL_DIR}/../audit-codebase/references/analysis-playbook.md`.
- Worktrees, commits, the test environment, the merge gate, and integration: `${CLAUDE_SKILL_DIR}/../pipeline/references/worktree-protocol.md`.
- Fix patterns and bypass tests per defect class: `references/fix-playbook.md`.

The sibling files normally live under `~/.claude/skills/`. If any is missing, apply the rules stated in this file. Search all callers, including indirect ones (aliases, re-exports, interface implementations, callbacks, registries, decorators, events, reflection), before concluding anything about reachability.

If the repository has only a legacy single-file root `REPORT.md` and no `audit/` directory, stop and ask the user to run `/audit-codebase --tick` once. That tick migrates the report into the `audit/` layout.

## Modes

- **Worktree** (the default in a git repository): each issue, or root-cause batch, gets `.claude/worktrees/F-NNN-<slug>` on branch `task/F-NNN-<slug>`, created from the default branch. Fix and commit there. Run the merge gate, rebase inside the worktree, and `git merge --ff-only` from the main checkout. Then remove the worktree and branch. With `--no-merge`, stop after a passing gate and leave the branch for review.
- **In place** (`--in-place`, or not a git repository): edit the current checkout. Commit only with `--commit`.
- **Worker** (started by a pipeline lane brief): see Worker mode. The brief's rules win where they differ from this file.

## Execution model: ticks

A tick fixes one issue, or one batch of issues that share a root cause or must change atomically.

- **Loop mode**: this invocation was started by `/loop` or by a scheduled-task or wakeup fire, or `--tick` was given. Run exactly one tick, then end with the status block.
- **Standalone**: run ticks back-to-back until no actionable issue remains. Verify and persist each one fully before starting the next.

Disk is the source of truth. At the start of every tick, re-read `audit/REPORT.md`, the selected issue file, and the git state. Conversation memory from earlier ticks may be compacted or stale. An `audit-codebase` loop, a pipeline, or the user may be changing the audit or the code at the same time.

### Tick procedure

1. **Orient.** Resolve the main checkout with `git rev-parse --show-toplevel`. On the first tick, or after compaction:
   - read applicable `CLAUDE.md`/`AGENTS.md` files and repository documentation;
   - learn the commit convention from `git log --oneline -20`, CLAUDE.md, and project memory (default: one line, no body, no trailers);
   - learn what the test suites need.

   On every tick: read `audit/REPORT.md` (its Conventions and the issue index), then the selected issue file and the `map.md` rows it links to. Record `git rev-parse HEAD`, `git status --short`, and `git worktree list`.
2. **Recover.** If an issue is `In progress` with Fix notes written by this skill (not by a lane that is still running), resume it before anything else. Find its worktree and branch, or its baseline and intended files in place mode. Then finish the fix, or discard only this skill's own work (remove its worktree and branch, or revert only the hunks it made in place), or mark the issue `Blocked` with the reason.
3. **Baseline checks.** If `audit/log.md` has no baseline at or near the current revision, run the targeted and broad safe checks once, and record their failures as pre-existing. Later ticks compare against this baseline.
4. **Select.** Take the next issue from the arguments. Otherwise pick by severity, then dependency, then smallest blast radius. Dependency order puts foundational layers first: test infrastructure, schema and contracts, authorization primitives, repositories, entry points, then UI and documentation.
   - Only `Open` issues are actionable.
   - Skip `Blocked` issues unless the issue file or the chat shows the blocker was answered.
   - Never act on a `Candidate`; it has not been validated.
5. **Claim.** Before editing any code, re-read the issue file and set `Status: In progress`, in both the file and its index row. Write Fix notes:
   - the date and the baseline HEAD;
   - in worktree mode: the worktree path and branch;
   - in place mode: files already dirty before this tick;
   - the files you intend to touch.

   This is the recovery point for an interrupted tick.
6. **Fix.** Revalidate, map the blast radius, write tests first, implement, attack the fix, verify in layers, and pass the gate, as described in the sections below.
7. **Integrate.** Worktree mode: follow the worktree protocol's integration steps. With `--no-merge`, record `Ready to merge: task/<slug> @ <sha>` instead. In place mode with `--commit`, commit as described under Commits.
8. **Record** the result, then **report** with the status block.

### Status block and loop control

End every tick with:

```text
FIX TICK — F-<id> <title>: resolved | ready-to-merge | disproven | partial | blocked
Changed: <files>; branch: <task/... or in place>; merged: <sha or no>
Verified: <gate commands → results>; tests executed: yes/no; bypass tests: <n> pass
Remaining: open <IDs by severity>; blocked <IDs with one-line questions>
Loop: continue | done | blocked
Noop: true | false
```

Only control the loop when the `/loop` input invokes this skill directly. When a pipeline or another caller invoked it, report the verdict and leave loop control to the caller.

- `continue`: actionable issues remain. Under self-paced `/loop`, reschedule soon (60–120 s).
- `done`: no `Open` issue remains (all resolved, superseded, or blocked with questions recorded). End the loop. Self-paced: call `ScheduleWakeup` with `stop: true`. Fixed interval: load `CronList` and `CronDelete` via ToolSearch (`select:CronList,CronDelete`), find the job whose prompt invokes this skill, and delete it. Do not call `ScheduleWakeup` from a fixed-interval cron tick.
- `blocked`: every remaining issue needs the user. End the loop as for `done`, and list the questions.

`Noop` is `false` whenever the tick changed code, a branch, or any audit file.

## Worker mode

A pipeline lane brief puts you in worker mode. It names your issues, your worktree (already created), the main checkout path, the test environment, and the gate. In this mode:

- **Code tree:** your worktree only, by absolute path or `git -C`. Never modify anything in the main checkout except your own issue files.
- **Ledger:** `audit/` is usually untracked, so it does not exist in your worktree. Reach it by absolute path in the main checkout. Edit only your own issue files: Status, Updated, Fix notes, and Resolution; you may refresh Evidence, Variants, and Blast radius. Never edit `audit/REPORT.md`, `map.md`, or `log.md`. Never create issue files; report new defects in your final report.
- **Status:** on claim, `In progress` with Fix notes. When an issue is fixed and committed, keep `In progress`, add `Ready to merge: task/<slug> @ <sha>` to Fix notes, and write the full Resolution section. The coordinator sets `Resolved` after merging.
- **Owner decisions:** when the Proposed fix recommends an option for a policy choice, implement it and add `Owner decision taken: <what>` to Fix notes. With no single recommendation, set `Blocked` with the question and move on.
- **Git:** commit on your branch only, one commit per issue, following the brief's commit convention. `git add` only your files, by name. Never push, force, amend, rebase, merge, `reset --hard`, or use bare `git stash`. The coordinator rebases and merges.
- **Generated code and migrations:** regenerate generated code, never hand-edit it. Add a migration only if the brief says so, using its placeholder number. Never edit an existing migration.
- **Gate:** run the brief's gate after your last commit, on a clean worktree, and save the log where the brief says, with `EXIT=` lines.
- **Final report:** follow the brief's format: one line per issue, owner decisions, gate results against the baseline, files changed, new defects, and merge-time actions.

## Scope and safety

- Preserve user changes. In place mode, if a file you must touch has uncommitted user edits that overlap the fix, stop, mark the issue `Blocked` with that reason, and move on. In worktree mode, before merging, stop if the main checkout has tracked changes that neither you nor the user's instructions account for.
- Treat generated output, vendored code, lockfiles, migrations, external services, and production state as boundaries. Change them only when the validated fix requires it.
- Stop and ask for direction when a valid fix requires a product decision (outside worker mode's owner-decision rule), a destructive migration, a secret, external coordination, or materially broader authority. Record the concrete question in Fix notes, set `Blocked`, and continue with other issues. Never mark such an issue resolved.
- Never touch protected worktrees or branches (anything that existed before you started), and never remove worktrees or branches you did not create.

## Revalidate by re-deriving the defect

Do not trust the issue's trace. Rebuild it:

1. Re-read every linked location. If lines drifted, re-locate by symbol and locator. Confirm that the symbols and the faulty behavior still exist.
2. Rebuild the relation graph around the defect: every caller of the faulty symbol, direct and indirect; every callee it relies on and that callee's contract; and every entry point that reaches it. Start from the issue's traces (`T-*`) and the Caller Index, then search beyond them.
3. For each path from a source or trigger to the defect, decide whether it can be triggered now. Paths the audit missed widen the scope; paths already guarded narrow it.
4. Check compensating logic: framework behavior, middleware, schemas and types, database constraints, feature flags, deployment configuration in the repository, recent changes, and existing tests that could disprove or narrow the issue.
5. Reproduce it with a failing test or a deterministic reproduction when practical. For security and concurrency issues, encode the violated invariant as a test rather than running an exploit against a live system.
6. Sweep for variants: search for the same root-cause pattern across the repository, starting from the issue's Variants list.

The outcome is confirmed, narrowed, widened, or disproven. If the issue is disproven or already fixed, make no implementation change: set `Status: Resolved` (already fixed) or `Rejected (reason)` (disproven), write the evidence in Resolution or Closure, remove any worktree you created for it, and end the tick.

## Map the blast radius before editing

The issue's Proposed fix and Blast radius sections are a starting point. Verify them rather than following them mechanically.

1. **Choose the choke point.** Fix at the layer that every vulnerable path passes through and that owns the invariant: the query builder rather than one handler, the path-resolution helper rather than one caller, the authorization policy rather than one route. Patching only the reported call site while sibling paths stay vulnerable is incomplete. Do not push the fix so low that it breaks legitimate callers.
2. **Enumerate everything the change touches:**
   - callers of each function whose behavior or signature changes, and what each passes and expects;
   - implementations and overrides of changed interfaces;
   - persisted or serialized shapes and their readers: database, caches, queues, API clients, other services, exports;
   - configuration, flags, documentation, and tests that assert the old behavior.
3. **Decide the fate of each caller.** For every caller, write down what changes for it: a new error or exception, rejected input that used to be accepted, a changed return value, or a performance change. Decide how each is handled. A caller that now receives an error it does not handle is a regression you are about to create.
4. **State the invariant:** "After the fix, on every path from sources S to K, guard G holds before K", or the equivalent correctness property.
5. **Plan the proof:** a regression test that fails before and passes after, negative tests for the relevant bypass classes (`references/fix-playbook.md`), and the gate commands.
6. **Note compatibility and migration concerns.** If they need a decision, block as described in Scope and safety.

Group issues into one batch only when they share a root cause or must change atomically. Otherwise fix and verify them one at a time so failures remain attributable.

## Write tests first

Add the regression test and the negative tests before the fix, and confirm they fail for the right reason. When a test cannot fail first (for example, because test infrastructure is missing), state why and use the strongest substitute: a deterministic script, a type-level assertion, or a documented manual trace. New integration tests must skip only through the project's standard helper, never a bare skip, so skip-as-failure flags catch them.

## Implement completely

1. Patch the root cause at the chosen choke point and at every confirmed variant, without unrelated cleanup.
2. Prefer structural fixes over filtering: parameterization, argv arrays, allowlists, safe APIs, canonicalize-then-check, types that make invalid states unrepresentable, and ownership scoping inside the query. Prefer these over escaping, denylists, and post-hoc checks.
3. Fail closed. Do not swallow errors, and do not convert failures into success.
4. Preserve API and data compatibility unless the issue explicitly requires a contract or migration change.
5. Validate input and authorization at trust boundaries, and enforce critical invariants again in the owning domain or database layer where appropriate.
6. Make state transitions, reservations, ownership changes, and idempotency guarantees atomic where concurrency matters.
7. Update comments or documentation that assert an invariant the fix changed.

Never weaken or delete a failing test merely to obtain a passing check. Never expose secrets, call production systems, or apply automatic broad fixes. Do not install new dependencies unless the Proposed fix requires them, and then say so.

## Attack the fix

After patching and before declaring success, try to break the fix:

1. **Re-trace every path.** Walk each path from revalidation, and each caller from the blast radius, through the new code. Confirm the guard runs on every route to the sink, suits the sink's context, runs after the final decode or normalization, and fails closed.
2. **Hunt for bypasses.** Look for alternate entry points that reach the sink without passing the choke point: other routes, jobs, CLI commands, admin or debug handlers, GraphQL or RPC twins, older API versions. Also try:
   - encoding and normalization variants;
   - type confusion (arrays, objects, numbers, `null`) and boundary values;
   - TOCTOU windows and concurrent requests;
   - error paths that skip the check, and configuration that disables it;
   - sibling APIs that do the same thing as the fixed sink.

   Follow the class-specific list in `references/fix-playbook.md`.
3. **Check the contract ripple.** Confirm that every caller handles the new behavior: new errors are propagated or handled, no caller crashes or silently drops work, and no caller now double-validates in a conflicting way.
4. **Review your own diff as a hostile reviewer.** Read `git diff` for the tick's files and look for new injection points, information leaks in error messages, resource leaks, performance regressions (N+1 queries, unbounded loops), broken invariants in shared code, and changed behavior outside the issue's scope.
5. **Sweep for variants again.** Search once more for the root-cause pattern, now that you understand it fully. Fix confirmed instances in this tick if they share the root cause. Otherwise record them as new defects (see Record the result).
6. **Get an independent review (optional).** For Critical and High issues, when the Agent tool is available, give a fresh subagent the issue, the invariant, and the diff, and ask it to find a bypass or a broken caller. Address what it finds, or record why it does not apply.

Tests supplement rather than replace this code-level proof.

## Verify in layers: the merge gate

Run safe, repository-native commands discovered from package metadata, CI workflows, and documentation:

1. the new tests and the nearest targeted tests;
2. typecheck, lint, and static checks for affected packages, without fix or write flags;
3. relevant integration or migration checks, against local disposable services when needed (see the worktree protocol's test environment), never production;
4. the broad test, typecheck, lint, and build commands, when reasonably bounded.

The gate passes only when **the relevant tests actually executed**. Turn skips into failures where the project supports it, and confirm the new regression test ran. Save the full gate output, with `EXIT=` lines, to a log in the scratchpad and cite it in the Resolution. Compare results with the recorded baseline, and distinguish regressions from pre-existing failures.

If the gate cannot run the relevant tests (for example, a database is unavailable and no local substitute is possible), do not merge. Record `Ready to merge (tests not executed: <reason>)` and leave the branch for review.

## Record the result

The audit files are the durable ledger. Re-read each one immediately before editing and apply targeted edits. If an edit fails because the file changed, re-read and reapply. Follow the ownership rules in the contract; in worker mode, the stricter worker rules apply.

1. **Issue file.** For an issue that is resolved and merged, set `Status: Resolved` and write the Resolution section: date, merged commit, invariant established, precise code and test links, bypass classes tested, gate commands and log path, and limitations. For a fix that is ready but not merged, keep `In progress` with the `Ready to merge` line and the full Resolution. For a partial fix, keep `In progress` or set `Blocked`, update Fix notes, and refresh Evidence, Variants, and Blast radius with what the fix revealed.
2. **Index** (not in worker mode). Update the issue's row in `audit/REPORT.md` and the counts line. When available, prefer `python3 ${CLAUDE_SKILL_DIR}/../audit-codebase/scripts/audit_index.py rebuild`. Do not edit the ledger, Conventions, or Coverage; the audit owns those.
3. **Map** (not in worker mode). Set affected traces (`T-*`) in `audit/map.md` to `Safe`, with the new guard linked. Refresh caller-index rows and line links the fix changed.
4. **Log** (not in worker mode). Append the gate commands and results to `audit/log.md`.
5. **New defects.** Outside worker mode, create a new issue file per the contract, with `Status: Candidate`, the next free ID, and the evidence, and add it to the index. In worker mode, list it in the final report. Never hide a new defect inside a resolution note.

Before finishing the tick, verify that the links you touched resolve and that their line numbers match the current files.

## Commits

- Follow the repository's convention (from `git log`, CLAUDE.md, and project memory). The default is one line, no body, no trailers, for example `fix(F-027): verify the social account belongs to the connecting workspace`.
- Worktree and worker modes: one commit per issue or root-cause batch, on the task branch. In place mode: commit only with `--commit`, on a branch other than the default (create `audit-fixes/<date>` if needed).
- Stage only the files changed for the issue, by name. Stage `audit/` files only when they are tracked and the edits in them are yours.
- Never push, amend, force, or bypass hooks.

## Completion criteria

An issue is resolved only when all of these hold:

- its original trigger, and every other path found during revalidation, no longer violates the stated invariant;
- bypass classes relevant to the defect were tested or explicitly ruled out;
- every caller affected by a changed contract was checked and handles the new behavior;
- duplicate instances and variants were addressed, or recorded as new defects;
- regression coverage demonstrates the fix, and the gate shows the relevant tests actually executed;
- broader checks pass, or the remaining pre-existing failures are clearly identified;
- the change is merged (or, with `--no-merge` or in worker mode, marked `Ready to merge`);
- the issue file records enough evidence for a later agent to verify the resolution without rescanning the repository.

When the loop ends, or standalone work finishes, report:

- resolved, ready-to-merge, and remaining issue IDs, and blocked issues with their questions;
- merged commits, unmerged branches, and worktrees left for review;
- gate results, pre-existing failures, and any migration or deployment follow-up.

Confirm that unrelated user changes were preserved.

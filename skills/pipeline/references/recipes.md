# Recipes: stage building blocks and default chains

Design each run from these blocks. Match the goal to a default chain, then adjust it to the repository's state. The user's explicit stages always win; keep them verbatim and fill in only what they leave out.

## Building blocks

| Block | What it does | Calls | Done when |
|---|---|---|---|
| **Cleanup** | Delete or untrack scratch files, fix `.gitignore`, remove dead config the user named | worktree task | committed and merged |
| **Migrate ledgers** | Convert a legacy root `REPORT.md` into `audit/`, or a root `PLAN.md` into `plans/` | `audit-codebase --tick` (P0) / `discover-and-plan --tick` | the legacy file is gone and the new layout checks clean |
| **Audit** | Map, trace, and record issues until the audit's run is Complete | `audit-codebase --tick` | the ledger state is `Complete` |
| **Validate** | Verify every `Candidate`: promote to `Open` with a Proposed fix, or reject | `audit-codebase --tick` with verification rows at the top of its queue; parallel verification workers for large batches | no `Candidate` issues remain |
| **Re-check** | Re-verify every `Open` issue against the current HEAD | an audit verification row covering all `Open` issues | every `Open` issue still holds, or is closed with evidence |
| **Fix lanes** | Fix `Open` issues in parallel worktree lanes, gated and merged serially | `fix-audit-findings` in worker mode, one lane per group | every lane merged, blocked with a question, or left unmerged with a reason |
| **Fix one by one** | Fix `Open` issues sequentially, one worktree each | `fix-audit-findings --tick` | no actionable `Open` issues remain |
| **Discover** | Turn a vague goal into Ready plan files | `discover-and-plan --tick` (interviews when the user is present, queues questions otherwise) | the plans are `Ready` |
| **Import plan** | Convert an approved plan the user points to (for example `~/.claude/plans/*.md`) into `plans/` | coordinator, following the plans contract | the plans are `Ready`, with every step and check kept |
| **Implement** | Build Ready plan tasks in dependency order; independent tasks run as parallel lanes | `implement-plan --tick`, or lanes in worker mode | every task `Done`, or `Blocked` with a question |
| **Readiness** | Run every CI job's commands locally, replay the container build steps where possible, and fix what blocks CI or deploy (dead scripts, stale docs and tests, lockfile drift) | worktree task(s) | CI-equivalent commands pass, or the remaining blockers are listed |
| **Update dependencies** | Update dependencies within the user's bounds; run the full gate; record advisories | worktree task per ecosystem | gated and merged, or reverted with a reason |
| **Re-audit** | A second full audit run that looks for missed issues and gives every `Open` issue a concrete Proposed fix | `audit-codebase --restart --tick` | run 2 is `Complete` |
| **Final validation** | Check that the ledgers are consistent, have fresh subagents try to refute each Critical/High `Open` issue, check that links resolve, do housekeeping, and write the summary | coordinator (plus `audit-codebase --tick` for leftovers) | the summary is written and the loop stopped |

## Default chains

Pick the closest chain and adapt it. Every chain ends with **Final validation**.

- **"Audit" / "review" / "find issues":** Migrate ledgers (if needed) → Audit → Validate → Final validation.
- **"Fix" / "fix the audit" / "work through the issues":** Re-check → Fix lanes (Fix one by one if there are only a few issues, or if they all share files) → Validate (new candidates raised by lanes) → Final validation.
- **"Plan" / "figure out" / "scope":** Discover → Final validation (plan consistency only).
- **"Build X" / "implement X" / "add feature X":** Discover (or Import plan if one exists) → Implement → Audit scoped to the changed area → Validate → Fix lanes for anything found → Final validation.
- **"Update" / "upgrade deps":** Update dependencies → Readiness → Final validation.
- **"Make it deploy-ready":** Readiness → Re-check (if an audit exists) → Fix lanes for issues that block deploying → Final validation.
- **"Full maintenance" / "everything":** Cleanup → Migrate ledgers → Audit → Validate → Fix lanes → Re-audit → Validate → Readiness → Final validation.

## Adjusting to the repository

- A fresh audit already exists (recent audited revision, or state `Complete`): skip Audit; start with Re-check.
- A legacy `REPORT.md` or `PLAN.md` exists: add Migrate ledgers first.
- An audit run is `In progress`: continue it instead of starting over.
- Plans with `Ready` tasks exist and the goal mentions building: Implement them before discovering more.
- No test suite, or suites that need unavailable services: add a test-environment step (disposable local services), or record the limitation. Fix lanes then merge only when their gate can actually run.
- The repository is not a git repository: no worktrees and no lanes. Run the skills in place, sequentially, and never commit.

## Ordering rules

- Put code-changing stages that restructure the tree (Cleanup, big refactors from imported plans) before audit and validation stages, so line references do not shift under the audit.
- Test-infrastructure fixes (making skipped tests run, adding CI services) go in the first fix wave, because they make every later gate meaningful.
- A Re-audit goes after fix lanes, so it audits the fixed code.
- Committing `audit/` and `plans/` happens only when the user asked for it, as the last step of Final validation.

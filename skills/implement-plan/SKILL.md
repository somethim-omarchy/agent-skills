---
name: implement-plan
description: Implement Ready plan tasks from plans/NNN-<slug>.md (written by the discover-and-plan skill), one task per resumable tick, each in its own git worktree and branch. It captures the plan's baseline before any edit, follows the steps in order, runs the plan's Verification section as a merge gate that must show the tests actually ran, commits following the repository's convention, fast-forward merges (unless --no-merge), and marks the plan Done with an Implementation record. It respects Depends on, treats anything the plan does not cover (a new dependency, a scope change, a failed assumption) as a question instead of a silent decision, and runs as a background lane worker for the pipeline skill. Use when asked to implement, build, execute, or ship a plan or plan number, or to work through Ready plans in a loop.
argument-hint: "[plan number ...] [--no-merge] [--tick]"
---

# Implement Plan

Build what a Ready plan describes, exactly, and prove it. Plans live in `plans/`, one task per file, with `plans/README.md` as the index. Follow the plans contract (`${CLAUDE_SKILL_DIR}/../discover-and-plan/references/plan-contract.md`) and the worktree protocol (`${CLAUDE_SKILL_DIR}/../pipeline/references/worktree-protocol.md`). The sibling files normally live under `~/.claude/skills/`; if one is missing, apply the rules stated here.

Invocation arguments (may be empty): $ARGUMENTS

- Plan numbers (`2`, `002`, or an epic number, which means all of its tasks): implement these, in dependency order. With none, implement every `Ready` task whose dependencies are `Done`.
- `--no-merge`: after a passing gate, leave the branch and worktree for review instead of merging.
- `--tick`: force loop-mode behavior (one task step per invocation) even when not started by `/loop`.

Typical use: `/implement-plan 2`, `/loop /implement-plan 1` (every task of epic 001, in order), or through `/pipeline`, which runs independent tasks as parallel lanes in worker mode.

## Execution model: ticks

- **Loop mode** (started by `/loop` or a wakeup, or `--tick` was given): one bounded step per tick. A task usually takes several ticks: set up and baseline, implement a group of steps, run the gate, integrate.
- **Standalone:** run steps back-to-back until the selected tasks are `Done` or `Blocked`.

Disk is the source of truth. Every tick re-reads the plan file, its parent epic, `plans/README.md`, the task's Implementation record, and the git state. Conversation memory may be compacted.

### Tick procedure

1. **Orient.** Resolve the main checkout. On the first tick, read CLAUDE.md/AGENTS.md, learn the commit convention (`git log --oneline -20`, CLAUDE.md, project memory; default: one line, no body, no trailers), and learn what the test suites need.
2. **Recover.** If a task's Implementation record shows work in progress, resume it from that record: worktree, branch, completed steps, and baseline location.
3. **Select.** Take the next task in dependency order. A task is actionable only when it is `Ready` and every `Depends on` task is `Done` (merged). Never start a task whose dependencies are unmerged.
4. **Set up.** Before the first edit:
   - create `.claude/worktrees/NNN-<slug>` on branch `task/NNN-<slug>` from the default branch;
   - install dependencies with the lockfile frozen;
   - capture every baseline the plan's Verification compares against (build output, compiled CSS, schema dump, route manifest, test results) at the starting commit, in the scratchpad.

   Write the Implementation record: worktree, branch, base commit, and baseline location.
5. **Implement.** Carry out the plan's steps in order, in the worktree, by absolute path or `git -C`. After each step, check its own "Done when" condition and note it in the record.
6. **Gate.** Run the plan's whole Verification section plus the repository's CI-equivalent checks, then follow the gate rules below.
7. **Commit and integrate.** Make one commit for the task, following the convention (for example `refactor(web): remove the zenncore scaffold (UI unchanged)`), staging files by name. Then rebase inside the worktree, rerun the gate if the rebase changed anything, and `git merge --ff-only` from the main checkout (after checking that it has no tracked changes this run did not make). Remove the worktree and branch. With `--no-merge`, stop after the gate and record `Ready to merge`.
8. **Record.** Set the task's State to `Done` and complete its Implementation record. Update `plans/README.md`. When every task of an epic is `Done`, set the epic to `Done`.
9. **Report** with the status block.

## Deviations are questions

The plan is the agreement. Stop and ask (user present) or mark the task `Blocked` with the question (user absent) when:

- a step needs something the plan does not cover: a new dependency, a config key, a broader file set, a changed public contract;
- an assumption the plan states turns out to be false, for example a cited line has moved in a way that changes the design, or a claimed-unused module is used;
- a verification item cannot pass without changing scope.

Record the question and the evidence in the Implementation record, keep the worktree for resumption, and continue with independent tasks. Small mechanical drift, such as moved line numbers or renamed-but-equivalent symbols, is not a deviation; fix it and note it.

## The gate

A task merges only when **its checks actually executed**:

- Every item of the plan's Verification section passed, or was recorded as `not run` with a reason (for example, Docker unavailable) together with the strongest substitute used. An item the plan calls the check that matters, such as a CSS diff or a schema equivalence proof, is never skippable.
- The repository's CI-equivalent commands pass: lint without write flags, typecheck, tests, and build. Failures must match the baseline's pre-existing failures exactly.
- Relevant tests ran rather than skipped. Turn skips into failures where the project supports it.
- The full output is saved to `<scratchpad>/lanes/NNN-<slug>-test.log` with `EXIT=` lines. **No log, no merge.**

## Worker mode

A pipeline brief puts you in worker mode, with the worktree already created. In this mode:

- Edit only files in your worktree, plus your own plan file's Implementation record in the main checkout (by absolute path). Never edit `plans/README.md`, other plans, or anything else in the main checkout.
- Commit once for the task, on your branch. Never push, force, amend, rebase, merge, `reset --hard`, or use bare `git stash`. The coordinator rebases, merges, and sets `Done`.
- Deviations: record the question, stop, and report it. Do not decide it.
- End with the brief's final report: done-on-branch (sha) or blocked (question), each verification item with its result, the baseline comparison, files changed, and merge-time actions.

## Status block and loop control

```text
IMPLEMENT TICK — plan NNN <title>: setup | step k/n | gate | merged | ready-to-merge | blocked
Worktree: <path or removed>; branch: <task/...>; commit: <sha or none>
Gate: <items passed / not run / failed>; tests executed: yes/no; log: <path>
Remaining: <Ready tasks in order>; blocked <numbers with questions>
Loop: continue | done | blocked
Noop: true | false
```

Only control the loop when the `/loop` input invokes this skill directly; otherwise leave loop control to the caller.

- `continue`: reschedule in 60–120 s.
- `done`: no actionable task remains. Stop the loop: self-paced, call `ScheduleWakeup` with `stop: true`; fixed interval, `CronList` then `CronDelete`.
- `blocked`: every remaining task waits on the user. Stop as for `done`, and list the questions.

## Safety

Preserve user changes. Never touch protected worktrees or branches (anything that existed before you started), and never remove ones you did not create. Never push, force, or bypass hooks. Never weaken a test or a verification item to pass the gate. Never access production systems or print secret values.

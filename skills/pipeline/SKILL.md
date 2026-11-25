---
name: pipeline
description: One entry point for any multi-step repository job (auditing, validating issues, fixing, discovery and planning, implementing plans, cleanup, dependency and deploy-readiness updates, re-audits) as a single resumable run under /loop. Give it a goal in plain words ("fix everything open in the audit, then re-audit", "plan and build SSO", "full maintenance pass") or explicit stages. It designs the stage chain, calls the other skills (audit-codebase, fix-audit-findings, discover-and-plan, implement-plan) as units of work, and keeps a spec and state file in .claude/runs/. It makes every code change in its own git worktree, merged fast-forward only after a gate proves the tests actually ran, and runs independent work as parallel background lanes. It owns loop control, records user decisions mid-run, and ends with housekeeping and an owner-facing summary. Use whenever the user wants to start, continue, or check on a fixing, discovery, update, or worktree chain, or says "pipeline", "maintenance run", "do all of this in a loop", or "use worktrees".
argument-hint: "<goal or stage spec> [--run <name>] [--dry-run] [--status]"
---

# Pipeline

You coordinate a multi-stage run toward the user's goal, one bounded step per tick. You design the stages, call the specialist skills to do the work, keep all progress on disk, and decide when the loop continues. Code changes happen only in per-task git worktrees and reach the main checkout only through fast-forward merges that passed a merge gate. Independent work runs in parallel as background worker lanes that you brief, supervise, rebase, gate, and merge.

Invocation arguments (may be empty): $ARGUMENTS

- Goal or stage spec: plain words, or explicit stages. Under `/loop` the same text repeats every tick; it identifies the run, it is not a new request each time.
- `--run <name>`: continue a specific run.
- `--dry-run`: design the stage chain, write it to the spec, show it with the run's name, and stop without doing any work. Start it afterwards with `/loop /pipeline --run <name>`.
- `--status`: read-only. Print the stage table, workers in flight, owner actions, and the last log lines of the run (the one named with `--run`, or the only active one), then stop. Never continues work and never touches loop control.
- No arguments: if exactly one run is active, continue it. Otherwise list the runs in `.claude/runs/` with their current stage, and ask which one to continue.

Typical use:

- `/loop /pipeline fix every open audit issue in parallel worktrees, then re-audit`
- `/loop /pipeline plan and build Google SSO`
- `/loop /pipeline full maintenance pass: clean up, audit, fix, re-audit, make it deploy-ready`
- `/pipeline --dry-run <goal>`, then `/loop /pipeline --run <name>` (preview the chain first)
- `/pipeline --status --run maintenance-2026-09-11` (check on a run)

References, in this skill's directory:

- `references/recipes.md`: stage building blocks, which skill each one calls, and the default chains for common goals.
- `references/run-files.md`: formats of the spec and state files.
- `references/worktree-protocol.md`: worktrees, lanes, test environments, the merge gate, and integration.
- `references/worker-briefs.md`: brief templates for fix lanes, verification workers, and plan-task workers.

## Skills it calls

| Skill | Used for | How it is called |
|---|---|---|
| `audit-codebase` | audits, migration of old reports, validating candidates, re-audits | Skill tool. Audits and re-audits run in its deep scan mode (a Workflow: bundle reviewers, then skeptics refuting each finding); the pipeline's own run counts as the opt-in. Run the scan as one stage step and wait for its notification, then file the issues before fixing starts. `--tick --classic` only for small watch re-audits |
| `fix-audit-findings` | fixing validated issues | in a worktree for a single issue; as a background lane worker (worker mode) for parallel fixes |
| `discover-and-plan` | turning a vague goal into `plans/NNN-*.md` tasks | Skill tool, `--tick` |
| `implement-plan` | building Ready plan tasks | in a worktree per task; as a lane worker for parallel tasks |

Their status blocks, including `Loop: done`, are **advisory**. Only this run decides whether the loop continues. Never call `ScheduleWakeup` with `stop: true`, or `CronDelete`, because a called skill said so.

## Files

- `.claude/runs/<name>-spec.md`: the spec. It holds the invocation text and the user's instructions verbatim, the stage chain you designed, run-local conventions, and user decisions appended with dates. It is authoritative. Read it every tick.
- `.claude/runs/<name>.md`: the state. It holds the stage table, stage-boundary checklists, lane tables, the environment, owner actions, follow-ups, and a one-line-per-tick log.

Add `.claude/runs/` to `.git/info/exclude`. These files are local tool state, never committed.

## Finding or creating the run

1. `--run <name>` given: use that run.
2. Otherwise, look for an active run (any stage not `Done`) whose recorded invocation text equals the arguments. Use it. Record and compare the invocation without the flags `--dry-run`, `--status`, and `--run`.
3. Otherwise, with a goal or stage text: create a new run named `<2–4 word slug>-<date>`.
4. If the arguments differ from an active run's invocation but clearly concern it (for example, the user added a stage), treat the new text as a user decision on that run, not as a new run. Ask if unsure and the user is present.

The user is **present** when this tick directly follows their own message. Otherwise treat them as absent. Never block on AskUserQuestion when they are absent.

### First tick: design the chain

1. **Survey the repository briefly.** Check the default branch and HEAD, `git status --short`, and `git worktree list` (every pre-existing worktree and branch becomes **protected**). Look for existing `audit/`, `plans/`, and `.claude/runs/`. Note CLAUDE.md/AGENTS.md, and the commit convention from `git log --oneline -20` and project memory (default: one-line messages, no body, no trailers). Check what the test suites need, and whether Docker and databases are available.
2. **Design the stages** from `references/recipes.md`: match the goal to a default chain, then adjust it to the repository's state. For example, skip the audit when a fresh one exists, add P0 migration when a legacy `REPORT.md` exists, add a readiness stage when the goal mentions deploying. Explicit stages from the user win over recipes; keep them verbatim.
3. **Write the spec and state files** per `references/run-files.md`, including the environment and the protected list.
4. **Show the stage table** in chat. If the user is present and a choice materially changes the chain (merge policy, scope, whether to fix or only report), ask once. Otherwise proceed, recording your defaults as run-local conventions.
5. With `--dry-run`, stop here. Otherwise start the first stage.

## Every tick

1. **Load.** Read the spec and the state file. Honor every run-local convention and user decision. Do not rely on conversation memory; it may be compacted.
2. **Workers.** If background workers are in flight, collect the ones that finished (their final reports, gate logs, and issue or plan files) and integrate them (see Parallel lanes). If some are still running and no independent step is available, this is a **waiting tick**: log it, set `Noop: true`, and do nothing else.
3. **Choose.** Continue the first stage that is not `Done`. A stage blocked on the user does not stop later stages that do not depend on it.
4. **Review the stage boundary.** Before starting a new stage, review what the previous stage produced and what the next one must settle. Consult the advisor when available. Record the result as an "Sx → Sy review" checklist in the state file, and follow it.
5. **Work** one bounded step: one skill tick, one worktree task step, one lane integration, or one batch of worker launches.
6. **Persist.** Update the stage row, the stage sections you changed, and the lane table. Append one log line: `T<n> <date> <stage>: <what happened>. Next: <step>`.
7. **Report** with the status block.

### User messages mid-run

When the user writes during the run:

- Record their decisions verbatim, with the date, under "User decisions" in the spec.
- Log the turn as `T<n>b (user turn): …`.
- If they add work, insert stage rows where it belongs, using suffixed IDs (`S5b`, `S8b`), and write the new stage's procedure into the spec next to the decision.
- Answer status questions from the state file.

### Owner actions

Collect everything the owner must do or know in the state file's Owner actions section, and relay it in the final summary:

- secrets to create, DNS or dashboard steps, deploy caveats, data resets;
- decisions taken on the owner's behalf, marked `(revertable)`;
- open product questions.

## Code changes: worktrees only

Follow `references/worktree-protocol.md`. In short:

- Every code-changing task gets `.claude/worktrees/<slug>` on branch `task/<slug>`, created from the current default branch after its dependencies have merged.
- Work there with absolute paths or `git -C`. Bash's working directory resets between calls. Do not use EnterWorktree, which moves the whole session.
- Ledgers (`audit/`, `plans/`, `.claude/runs/`) live in the main checkout. Workers reach them by absolute path and write only what they own.
- A task merges only through the gate: its tests actually executed, and the gate log exists. Then rebase in the worktree, rerun the gate if the rebase changed anything, run `git merge --ff-only` from the main checkout, and remove the worktree and branch.
- Before every merge, check `git status` in the main checkout. Stop and ask if it has tracked changes this run did not make.
- Unmerged tasks keep their worktree and branch and are listed in the final summary.

Merging into the default branch is the pipeline's default, because the user started the run to get the work done. If the user asked for review first, or the spec says `merge: no`, leave gated branches unmerged and list them.

## Parallel lanes

Use lanes when a stage has several independent code tasks (open audit issues, plan tasks whose dependencies are satisfied) or many verifications:

1. **Group** work into lanes by the files each task will touch and by shared root cause. Tasks sharing a file go in one lane, in sequence. Serialize generated-code and contract lanes, migration-owning lanes, and heavy build lanes as the protocol describes. Order lanes into waves: test-infrastructure fixes that make gates meaningful go first.
2. **Prepare** each lane: worktree, branch, per-lane test databases, the environment block, and a brief filled from `references/worker-briefs.md` and saved in the scratchpad.
3. **Launch** at most 4–5 background agents at once (Agent tool, background), one per lane.
4. **Integrate** serially as lanes finish. Read the final report, check the gate log, rebase, resolve conflicts, rerun the gate if needed, ff-merge, and clean up. Then update the ledgers workers may not touch: the audit index and log, the plan index, and statuses such as `Resolved` and `Done`. File the new defects that workers reported as `Candidate` issues.
5. **Record** each lane's status, commits, and gate log path in the state file's lane table.

Subagents cannot run `git rebase`, so the coordinator always rebases. Workers never merge, push, or edit shared ledgers.

## Test environment

If the suites need services and Docker is not available, start disposable local substitutes under the scratchpad: for example an embedded Postgres on a non-default port, a Redis-compatible server, and an SMTP sink. Record ports, credentials, and the environment block in the state file. Give each lane its own database. Stop the services in housekeeping. Never point tests at production or real secrets.

## Housekeeping and the final summary

In the last stage, or when the run ends early:

- `git worktree list` shows only protected worktrees and deliberately unmerged lanes.
- Disposable services are stopped.
- `git status --short` in the main checkout shows only intended changes. Commit ledgers (`audit/`, `plans/`) only when the spec says so.
- Every stage row is `Done`, `Blocked` (with its question), or `Skipped` (with a reason).

Then write the summary in the state file and in chat: commits and merges, stage outcomes, counts (issues by severity and status, plans done), owner actions, decisions taken on the owner's behalf, anything blocked or not run, and unmerged branches with the reason for each. Stop the loop.

## Status block and loop control

End every tick with:

```text
PIPELINE TICK <n> — <run> — <stage> — <what was done>
Next: <stage and step>
Workers in flight: <k>
Loop: continue | waiting | done | blocked
Noop: true | false
```

- `continue`: reschedule in 60–120 s.
- `waiting`: only background workers are pending. Schedule a 1200–1800 s fallback; their completion notifications wake the loop sooner.
- `done`: the final stage is `Done`. Stop the loop. Self-paced: call `ScheduleWakeup` with `stop: true`. Fixed interval: find this job with `CronList` and `CronDelete` it.
- `blocked`: every remaining stage needs the user. Stop the loop as for `done`, and ask.

When invoked without `/loop` (standalone), run steps back-to-back until the run is done or blocked, persisting after each step.

## Safety

Never push, force, amend shared history, `reset --hard`, or use bare `git stash`. Never touch protected worktrees or branches, and never remove worktrees or branches this run did not create. Never access production systems or print secret values. Never weaken a test to pass a gate.

# Worktree protocol

Shared by `pipeline`, `fix-audit-findings`, and `implement-plan`. It applies to every code change made through them in a git repository.

## 1. Layout and naming

- Worktree: `<repo>/.claude/worktrees/<slug>`. Branch: `task/<slug>`.
- Slugs: `fix-<lane>` for fix lanes, `F-NNN-<issue-slug>` for single-issue fixes, `NNN-<plan-slug>` for plan tasks, `<stage-slug>` for stage tasks such as `cleanup-tmp` or `deploy-readiness`.
- `.claude/worktrees/` must be ignored locally: check `git check-ignore`; if it is not ignored, add it to `.git/info/exclude`, never to `.gitignore`.
- Protected: every worktree and branch that existed before the run or task started. Never modify, rebase, or remove them.

## 2. Creating a worktree

```bash
git -C <repo> worktree add <repo>/.claude/worktrees/<slug> -b task/<slug> <default-branch>
```

- Branch from the current default branch, and only after the task's dependencies have merged.
- Work only through absolute paths or `git -C <worktree>`. Bash's working directory resets between calls. Do not use EnterWorktree; it moves the whole session.
- Install dependencies inside the worktree with the lockfile frozen (`bun install --frozen-lockfile`, `npm ci`, `go mod download`, and so on). A worktree starts with no `node_modules` or build output.
- Capture any baseline the gate compares against (build output, CSS, schema dump, test results) at the starting commit, **before** the first edit, and store it in the scratchpad.

## 3. Ledgers live in the main checkout

`audit/`, `plans/`, and `.claude/runs/` are usually untracked, so they do **not** exist inside worktrees. Workers read and write them by absolute path in the main checkout, and only the parts they own:

- fix workers: their own issue files (Status, Updated, Fix notes, Resolution, and refreshed Evidence, Variants, and Blast radius);
- plan workers: their own plan file's Implementation record;
- verification workers: their own issue files.

Only the coordinator edits `audit/REPORT.md`, `audit/map.md`, `audit/log.md`, `plans/README.md`, and the run files. Workers never create issue files; they report new defects, and the coordinator files them.

## 4. Commits

- Follow the repository's convention, from `git log --oneline -20`, CLAUDE.md/AGENTS.md, and project memory. The default is one line, no body, no trailers. Examples: `fix(F-114): run DB-backed tests in CI`, `refactor(web): remove the zenncore scaffold (UI unchanged)`.
- Make one commit per issue, root-cause batch, or plan task.
- `git add` only the files you changed, by name. Never `git add -A` or `git add .`.

## 5. What workers never do

Workers never:

- rebase, merge, push, amend, force, `reset --hard`, or use bare `git stash` (subagents cannot run `git rebase` anyway);
- edit anything in the main checkout except the ledger files they own;
- touch other worktrees or protected branches;
- install new dependencies or change lockfiles, unless their task explicitly requires it (and then they say so);
- hand-edit generated code; they regenerate it with the repository's generator;
- edit an existing migration. A new migration uses the placeholder number from the brief, and the coordinator renumbers it at merge.

## 6. Lanes

- **Grouping:** tasks whose changes touch any common file, or that share a root cause, go in one lane and run in sequence. Lanes must be file-disjoint.
- **Serialized kinds:** only one lane at a time may change each of the following:
  - API contracts or generated code; on a conflict, take the other side and regenerate, never hand-merge;
  - migrations; pre-assign placeholder numbers and renumber at merge so versions follow merge order;
  - heavy builds, such as one frontend production-build lane at a time.
- **Waves:** wave 0 fixes test infrastructure (tests that skip or are broken, missing CI services), because it makes every later gate meaningful. Later waves follow dependency order.
- **Concurrency:** at most 4–5 background lanes at once.
- **Owner-decision issues:** when a Proposed fix names a recommended option for a policy choice, the lane implements it and records `Owner decision taken: <what>` so the owner can revert it. With no single recommendation, the lane blocks with the question.

## 7. Test environment

- Prefer the project's own test services. If Docker or the databases are unavailable, the coordinator starts disposable substitutes in the scratchpad: an embedded Postgres on a non-default port, a Redis-compatible server, an SMTP sink. It records ports, credentials, and the environment block in the run's state file.
- Give each lane its own databases (for example `lane_<slug>` and `lane_<slug>_mig`), migrated from the lane's worktree. Shared services are fine when they are stateless for tests.
- Turn skips into failures where the project supports it (for example an env flag like `JOB_TEST_REQUIRED=1`). New integration tests must skip only through the project's standard helper, never a bare skip, so the flag catches them.
- Never point tests at production systems or real secrets.

## 8. The merge gate

A branch merges only when **its tests actually executed**: not skipped, not "passed" because the relevant tests never ran.

- Run the gate after the last commit, on a clean worktree (`git status --short` empty).
- **Backend:** vet/lint plus the full test suite against the lane's own databases, with skips turned into failures.
- **Frontend:** boundary and lint checks without write flags, typecheck, unit tests, and a production build. When styles or dependencies change, add an output diff against the baseline (for example compiled CSS).
- Save the full output to `<scratchpad>/lanes/<slug>-test.log`, with `EXIT=<code>` lines. **No log, no merge.**
- Failures must match the recorded baseline's pre-existing failures exactly. Any new failure blocks the merge until it is fixed or explained.

## 9. Integration (coordinator only)

1. Check the main checkout with `git status --short`. If it has tracked changes the run did not make, stop and ask.
2. Rebase the task branch onto the default branch **inside the worktree**. Resolve conflicts:
   - keep both sides where both changes are intended;
   - regenerate generated code instead of merging it;
   - renumber migrations to the next free version;
   - watch for silent semantic collisions, such as duplicate test helpers, renamed symbols, or double registration.
3. If the rebase changed anything, rerun the gate and save `<slug>-rebased-test.log`.
4. From the main checkout, run `git merge --ff-only task/<slug>`.
5. Remove the worktree (`git worktree remove`) and delete the branch (`git branch -d`). Delete only what this run created.
6. Update the ledgers: issue status `Resolved` (the Resolution section cites the merged commit), plan state `Done` (with the Implementation record), index rows, the log, and the lane table.
7. Refresh shared state in the main checkout when needed, for example reinstall dependencies after a lockfile change.

## 10. Unmerged work

A lane that fails its gate, needs a decision, or can only run skipped tests keeps its worktree and branch. Record the reason in the lane table and in its issue or plan file. The final summary lists every unmerged branch with the next step for the owner.

# Run files

Both files live in `.claude/runs/` in the main checkout, excluded via `.git/info/exclude`.

## `<name>-spec.md`

~~~markdown
# Spec: <name>

Every tick reads this spec and the state file (<name>.md).

Invocation (verbatim; used to recognize this run on later ticks): <the /pipeline arguments>

---

<the user's instructions, verbatim>

---

Stage chain (designed on the first tick from references/recipes.md; the user's explicit stages kept verbatim):

S1 <block> — <what exactly, which skill and args, done-when>
S2 …

---

Run-local conventions (added by the run):
- Commit messages: <convention found in git log / CLAUDE.md / project memory>.
- Ticks are scheduled 60–120 s apart; waiting ticks use a 1200–1800 s fallback.
- <any other convention the run adopted, one line each>

---

User decisions, <date> (<the question they answered, if any>):
- <decision, quoting the user where it matters>

<stage procedures the user added, next to the decision that created them, e.g. "S8b Parallel fixes …">
~~~

Append decisions; never rewrite earlier ones. When a decision changes an earlier instruction, say which one it overrides.

## `<name>.md`

~~~markdown
# <Run title>

Repository: <absolute path>. Disk is the source of truth; every tick reads this file first,
continues the first stage that isn't Done, updates the table, and appends one log line.

Full stage spec (verbatim): .claude/runs/<name>-spec.md. Read it every tick too.

Protected (never touch): <pre-existing worktrees and branches>.
Never push, force, or `reset --hard`. Only remove worktrees/branches this run created.

## Environment

- Default branch and start HEAD; commit convention; test services (ports, credentials, env block); tools unavailable (e.g. Docker socket) and the substitutes used.

## Stages

| Stage | Status | Worktree/branch | Commit | Resume note |
|---|---|---|---|---|
| S1 <title> | Done | (removed) task/<slug> | <sha> | <one line> |
| S2 <title> | In progress | (main checkout, audit/ only) | | <where to resume> |

Statuses: Pending | In progress | Done | Blocked (question) | Skipped (reason).

## <Sx → Sy review> (checklists from stage-boundary reviews; follow them)

## <Stage> plan / lanes

| Lane | Tasks | Wave | Status | Commit(s) | Gate log |
|---|---|---|---|---|---|

Rules specific to this stage's lanes (serialization, migration numbering, build lanes, templates used).

## Owner actions (for the final summary)

- Secrets, DNS, dashboards, deploy caveats, data resets.
- Decisions taken on the owner's behalf, marked (revertable).
- Open product questions.

## Follow-ups

Work discovered along the way that belongs to a later stage or lane.

## Log

- T1 <date> S1: <what happened>. Next: <step>.
- T1b <date> (user turn): <decision recorded>.
~~~

Keep the Resume note and log lines to one line each; details belong in the stage sections or in the artifacts themselves (issue files, plan files, gate logs).

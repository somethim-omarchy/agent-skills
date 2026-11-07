---
name: discover-and-plan
description: Discover and refine a requested codebase change through a context-aware user interview, inspect the repository so questions and proposals fit the actual product and architecture, estimate implementation effort with assumptions and uncertainty, and write execution-ready plans under plans/ — one task per file, named after the task (plans/NNN-<task-slug>.md, like git issues), with a plans/README.md index — without implementing the work. Discovery state persists in the plan file, so it can run in resumable ticks under /loop (researching between answers without blocking on an absent user) or standalone. Use when a request is vague, broad, product-oriented, or needs requirements gathering, scoping, acceptance criteria, technical planning, task breakdown, or a time estimate before coding.
argument-hint: "[desired change | plan number] [--tick]"
---

# Discover and Plan

Clarify the desired outcome through repository research and a short adaptive interview, then produce execution-ready plans under `plans/` at the repository root. Do not implement the plans or modify any file outside `plans/`.

Plans work like git issues: **one task per file**, named after the task it handles, and listed in an index.

- `plans/README.md`: the index of every plan, with status, type, parent, estimate, and date.
- `plans/NNN-<task-slug>.md`: one plan. `NNN` is the next free three-digit number, and the slug is 2–6 kebab-case words naming the task (`plans/014-google-sso-login.md`). Never renumber or rename a plan file after creation.

A request that turns out to hold several independently deliverable tasks becomes an **epic**. The epic file keeps the request-level material (outcome, requirements, decisions, discovery record, overall estimate) and links one **task** file per deliverable, each with `Parent` and `Depends on` fields. A request that is a single deliverable stays one task file. Follow `references/plan-contract.md` for the formats.

The plan file doubles as discovery state. From the first tick it exists as a clearly marked draft, holding the research ledger, the question queue, and the answers, so work survives interruptions, compaction, and loop ticks.

Invocation arguments (may be empty): $ARGUMENTS

- Desired change: free text describing what the user wants. Under `/loop` the same text arrives on every tick; treat it as the standing request, not a new one each time.
- Plan number (for example `14` or `014`): continue or revise that plan.
- `--tick`: force loop-mode behavior even when not started by `/loop`.

Typical use: `/discover-and-plan add SSO login` (interactive, standalone), `/loop /discover-and-plan add SSO login` (keeps researching and integrating answers across ticks until the plan is Ready), or `/discover-and-plan 14` (resume plan 014).

## Execution model: ticks

A tick re-reads the plan file, advances discovery by one step, persists, and reports status.

- **Loop mode**: this invocation was started by `/loop` (its instructions are in the current turn), by a scheduled-task or wakeup fire, or with `--tick`. Run one tick, then end with the status block.
- **Standalone**: run ticks back-to-back, interviewing interactively, until the plan is `Ready` or the user stops.

Disk is the source of truth. Re-read the plan file and the index at the start of every tick. The user may have answered questions by editing the file directly, and conversation memory from earlier ticks may be compacted.

### Asking without stalling the loop

The user is **present** when this tick directly follows their own message: the `/loop` or skill invocation they just typed, or a reply they just sent. Otherwise (a timer-fired tick), treat them as **absent**.

- **Present:** ask through the AskUserQuestion tool, as in a normal interview.
- **Absent:** never block on AskUserQuestion. Post the questions as plain text, add them to the question queue with status `pending`, and spend the tick on research that does not depend on the answers.
- **Answers:** they can arrive in chat or as edits to the queue in the plan file. When you see an answer, record it in the queue immediately with the date, and mark the question `answered`, `delegated` (the user said "you decide"), or `withdrawn`.

### Tick procedure

1. **Load state.** Resolve the repository root with `git rev-parse --show-toplevel` when possible. Read `plans/README.md` and `git status --short`.
2. **Find the plan this invocation is about:**
   - A plan number in the arguments: use that file.
   - Request text: look for a non-`Ready` plan whose `Request` field matches it. If there is none, create the next number with a draft for the request, and add it to the index.
   - The request overlaps an existing plan (same feature area or outcome): if the user is present, ask whether to extend that plan or open a new one. If absent, open a new plan and record the overlap under Open questions.
   - A legacy root `PLAN.md` exists: migrate it to `plans/NNN-<slug>.md` with its content intact, add it to the index, and remove the root file, before anything else.
   - No request, no number, and no draft: if the user is present, ask what they want to achieve. Otherwise report `blocked`.
3. **Advance one step** of the phase recorded in the plan's Discovery Progress:
   - **Research:** investigate the next research-ledger area (see Ground the conversation in the project), and record facts with links. Generate candidate questions that only the user can answer.
   - **Interview:** integrate new answers, investigate newly relevant code, then ask the next one to three decision-changing questions.
   - **Confirm:** present the compact requirements summary, including the proposed task breakdown, and ask for confirmation or corrections.
   - **Finalize:** estimate, write the full plan, split it into task files if the breakdown has more than one deliverable, and set everything to `Ready`.
4. **Persist** the plan file(s) and the index row(s). Re-read before editing, and merge any edits the user made.
5. **Report** with the status block.

### Status block and loop control

End every tick with:

```text
PLAN TICK <n> — plans/<NNN-slug>.md — <phase> — <status>
Did: <research areas covered, answers integrated, questions asked>
Waiting on: <pending question IDs, or confirmation, or nothing>
Loop: continue | waiting | done | blocked
Noop: true | false
```

Only control the loop when the `/loop` input invokes this skill directly. When a pipeline or another caller invoked it, report the verdict and leave loop control to the caller.

Map the verdict to loop control:

- `continue`: research areas or new answers remain to process. Under self-paced `/loop`, reschedule soon (60–120 s).
- `waiting`: only user answers or confirmation block progress, and research is saturated. Report `Noop: true` when nothing new arrived. Self-paced heartbeat: 1200–1800 s. After three consecutive waiting ticks with nothing new, end the loop as for `done`. Tell the user to answer in chat or in the plan file, then run `/loop /discover-and-plan <number>` again (or reply directly while the session is open).
- `done`: the plan and all its task files are `Ready`. End the loop. Self-paced: call `ScheduleWakeup` with `stop: true`. Fixed interval: load `CronList` and `CronDelete` via ToolSearch (`select:CronList,CronDelete`), find the job whose prompt invokes this skill, and delete it. Do not call `ScheduleWakeup` from a fixed-interval cron tick.
- `blocked`: the missing request or an overlap decision needs the user. End the loop as for `done`, and state the question.

## Ground the conversation in the project

Seed the research ledger with these areas, and add areas as the request's shape becomes clear:

1. Inventory project Markdown with `rg --files -g '*.md' -g '*.mdx'`. Read applicable `CLAUDE.md`/`AGENTS.md` files first. Then read the relevant README files, product/domain notes, architecture documents, ADRs, existing plans in `plans/`, audit issues in `audit/issues/`, and feature documentation. Use headings and targeted searches to triage large documentation sets instead of loading unrelated prose.
2. Read manifests, configuration, and a compact project file inventory.
3. Trace the existing feature area from entry points through data, UI/API surfaces, services, integrations, and tests. Inspect enough actual code to distinguish current behavior from assumptions.
4. For each component the change will likely touch, find its callers and dependents, including indirect ones (re-exports, interface implementations, registries, events, configuration-driven wiring), plus the persisted or serialized shapes it owns. This change surface drives task boundaries, risks, and the estimate.
5. Note reusable components, established patterns, and platform constraints.

Build a context model of the product, users, domain vocabulary, architectural conventions, constraints, and reusable components before asking detailed questions. Keep it in the plan's Project Context section, not only in conversation memory.

Treat Markdown as useful project intent and history, not guaranteed current behavior. Check relevant claims against the current implementation and configuration. Surface material documentation/code conflicts as uncertainty, or as a question when they change the proposed scope.

Use repository evidence to keep questions relevant. Do not ask for information already answerable from the codebase. Do not import generic feature assumptions from unrelated product types. When the requested feature conflicts with project conventions or platform constraints, explain the evidence and ask about the actual tradeoff.

## Conduct an adaptive interview

Start by briefly reflecting what the user appears to want, plus any important project facts discovered. Ask one to three concise, decision-changing questions per turn; prefer one when it unlocks the next branch. Continue the back-and-forth rather than presenting a long questionnaire.

Prioritize unresolved decisions in this order:

1. target users and the problem or outcome;
2. in-scope behavior and explicit non-goals;
3. user journey, states, inputs, outputs, and edge/error behavior;
4. data sources, persistence, permissions, integrations, and compatibility;
5. visual or interaction expectations when applicable;
6. acceptance criteria, rollout, migration, observability, and validation;
7. delivery constraints that materially affect scope or estimate.

Offer two or three project-compatible options when that makes a decision easier, recommend one with a short reason, and allow a free-form answer. Ask for examples only when they materially reduce ambiguity. Challenge contradictions and costly hidden implications politely.

After each answer, update the working requirements and investigate newly relevant code before asking the next question. Do not repeat resolved questions; the queue shows what was already asked. If the user explicitly delegates a choice, select the option most consistent with repository patterns and record it as an assumption.

## Decide when discovery is complete

Continue until all of the following are true:

- the desired user-visible outcome and success criteria are concrete;
- scope and non-goals are explicit;
- important behavior, states, boundaries, and failure cases are understood;
- the affected architecture, its callers and dependents, and its dependencies are located in the repository;
- unresolved choices no longer change the implementation shape or estimate materially;
- assumptions and genuine unknowns can be stated honestly.

Then present a compact requirements summary and the proposed task breakdown, and ask the user to confirm or correct them. Record the confirmation (date and any corrections) in Discovery Progress before finalizing. Do not seek confirmation again for trivial wording changes. If the user asks to proceed despite unknowns, write them as assumptions or blocking decisions and widen the estimate accordingly.

## Break the work into tasks

A task is one independently reviewable and shippable deliverable, typically a few hours to a few days of effort, with its own acceptance criteria. Split a request into several tasks when parts can be built, reviewed, or released separately, or when they have different owners or dependencies. Keep it as one task when the parts only make sense together.

For an epic:

- The epic file keeps outcome, project context, confirmed requirements, non-goals, overall acceptance criteria, technical approach, rollout, risks, decisions, the discovery record, and a task table.
- Each task file has `Parent`, `Depends on`, its slice of acceptance criteria, implementation steps, verification, and its own estimate.
- Dependencies between tasks must form a sequence another agent can follow.

## Estimate responsibly

Estimate the agreed scope only after inspecting affected code. Use engineering effort, not promises: give a likely range in engineer-hours or engineer-days, plus a wider range when uncertainty is material. Estimate each task, sum them in the epic, and state whether tasks can overlap. Do not convert effort into a calendar delivery date unless team size, availability, review/deployment process, and dependencies are known.

Include testing, review/fix iterations, migrations, documentation, and rollout when applicable. Let the measured change surface (callers, dependents, persisted shapes, tests to update) drive the range. Identify assumptions, excluded work, external dependencies, principal uncertainty drivers, and the confidence level. Avoid false precision, and do not silently treat AI execution speed as equivalent to production delivery effort.

## Write the plan files

Follow `references/plan-contract.md`. During discovery, keep the plan file a draft: status banner, Discovery Progress, and whatever sections are already grounded, with unknown parts marked `TBD`. At finalization, make every implementation step executable by another agent: cite repository files and symbols with repository-root links, describe intended behavior and dependencies, and attach verification and acceptance criteria. Separate facts, confirmed decisions, assumptions, and open questions.

Write no source patches. Before finishing each tick, verify that:

- the links you added resolve;
- the index matches the plan files;
- `git status --short` shows no skill-created change outside `plans/`.

Once the plan is `Ready`, report the file(s) created and the headline estimate. Point the user to the next step: `/implement-plan <number>` builds the tasks, each in its own worktree, and `/loop /pipeline plan and build …` runs discovery and implementation as one chain.

If the user provides an already-approved plan from elsewhere (for example `~/.claude/plans/*.md`), import it instead of re-interviewing: convert it into the contract's epic and task files, keep every step, warning, and verification item verbatim in meaning, check every file and line it cites against the current tree (correcting drift and noting each correction), and mark it `Ready`.

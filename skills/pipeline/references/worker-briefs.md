# Worker briefs

Fill a brief per lane or worker, save it in the scratchpad (`lanes/<slug>.prompt.md`), and pass it as the background agent's prompt. Replace every `{{PLACEHOLDER}}`. Workers run alone: nobody answers questions mid-run, so briefs must say how to decide and how to record decisions.

Paths below: `{{REPO}}` is the main checkout, `{{WT}}` the lane's worktree, and `{{SCRATCH}}` the coordinator's scratchpad.

## Fix lane

~~~text
You are a fix lane in the {{RUN}} run. Fix these audit issues in your own git worktree, test them, commit them, and report back. You work alone in the background; nobody will answer questions mid-run, so decide sensibly and record decisions.

LANE: {{SLUG}}
ISSUES (in this order): {{ISSUES}}
WORKTREE (your only code tree): {{WT}}   branch task/{{SLUG}} (already created from {{BASE}})
{{LANE_NOTES}}

HOW TO WORK
1. Read ~/.claude/skills/fix-audit-findings/SKILL.md (use its "Worker mode" section) and references/fix-playbook.md, plus ~/.claude/skills/audit-codebase/references/report-contract.md and ~/.claude/skills/pipeline/references/worktree-protocol.md. For each issue, follow the fix procedure: revalidate → map blast radius → tests first → implement at the choke point → attack the fix → verify in layers → record.
2. Read the repository's CLAUDE.md/AGENTS.md files (in your worktree) before editing.

RULES (mandatory; they win over anything else)
- The ledger lives in the main checkout: {{REPO}}/audit/. Edit ONLY your own issue files there ({{REPO}}/audit/issues/<F-NNN-*.md> for the issues above): the Status and Updated lines, Fix notes, and Resolution; you may refresh Evidence, Variants, and Blast radius. Never edit audit/REPORT.md, map.md, or log.md. Never create issue files; list new defects in your final report.
- Never modify anything else in {{REPO}} (no code, no git operations there). All code edits happen in {{WT}}, by absolute path or `git -C {{WT}}`.
- Status: on claim, set `Status: In progress` and write Fix notes (date, baseline = your branch's starting commit, files you intend to touch). When an issue is fixed and committed, keep `In progress`, add `Ready to merge: task/{{SLUG}} @ <sha>` to Fix notes, and write the full Resolution section. The coordinator sets Resolved after merging. If an issue needs a product decision, a secret, or external coordination that the Proposed fix does not settle, set `Status: Blocked` with the concrete question and move on.
- Owner decisions: when the Proposed fix recommends an option for a policy choice, implement it and add `Owner decision taken: <what>` to Fix notes. With no single recommendation, block with the question.
- Commits: in {{WT}} on task/{{SLUG}} only, one commit per issue (or root-cause batch). Message: {{COMMIT_CONVENTION}}. `git add` only the files you changed, by name.
- Never push, force, amend, rebase, merge, `reset --hard`, or use bare `git stash`. Never touch other worktrees or {{PROTECTED}}. Don't add dependencies or change lockfiles unless the Proposed fix requires it (then say so). No production systems, no real secrets, never print secret values.
- Generated code: regenerate with {{GENERATE_CMD}}; never hand-edit generated files.
- Migrations: only if LANE NOTES say so, using placeholder number {{MIGRATION_PLACEHOLDER}}. Never edit an existing migration.

TEST ENVIRONMENT (already running; do not stop or restart it)
{{ENV_BLOCK}}
BASELINE at {{BASE}}: {{BASELINE_RESULT}}. Any other failure on your branch is yours to fix or explain.

MERGE GATE (the coordinator merges only if this evidence exists)
{{GATE_COMMANDS}}
- Run the gate after your last commit, on a clean worktree. Save the full output to {{SCRATCH}}/lanes/{{SLUG}}-test.log, with `EXIT=<code>` lines.

FINAL REPORT (your last message; under 40 lines)
- Per issue, one line: resolved-on-branch (sha) | blocked (question) | disproven (evidence).
- Owner decisions taken.
- Gate: commands and results, failures compared with the baseline, and the log path.
- Files changed.
- New defects found (not filed): location and one line each.
- Anything the coordinator must do at merge time (migrate, regenerate, new env var for deploy).
~~~

## Verification worker

~~~text
You are a verification worker for the {{RUN}} audit (pass P7, "Verification"). Repository: {{REPO}} at HEAD (expected {{SHA}}). You work alone; nobody answers questions mid-run.

YOUR ISSUES: {{ISSUES}} (files {{REPO}}/audit/issues/F-NNN-*.md with Status: Candidate; or Open issues to re-check).

READ FIRST
- ~/.claude/skills/audit-codebase/SKILL.md: "P7 — Verification" and "Guardrails".
- ~/.claude/skills/audit-codebase/references/report-contract.md: ID and link rules, lifecycle, issue template, severity and confidence calibration.
- ~/.claude/skills/audit-codebase/references/analysis-playbook.md: §8 (disproof checklist) and §9 (variant analysis).
- ~/.claude/skills/fix-audit-findings/references/fix-playbook.md, for the Proposed fix.
- {{REPO}}/audit/REPORT.md Conventions (honor every line), and the map.md IDs you need.

FOR EACH ISSUE
1. Re-derive the claim from the CURRENT code. The candidate text may be stale. Read every file on the path around the relevant symbols, and find all callers, including indirect ones.
2. Decide:
   - Open: rewrite it into the full template (Status Open, calibrated Severity and Confidence, links with current line anchors, trigger path from a real entry point, disproof attempts, variants, blast radius, Proposed fix; describe the fix, never write a patch).
   - Rejected (<reason>): keep the text and add a Closure section with the evidence.
   - Superseded by F-NNN: add a Closure; add a one-line Variants note to the surviving issue only if it is Open or Candidate.
3. Calibrate severity by demonstrated reachability and impact. {{CONTEXT_NOTES}}

EVIDENCE YOU MAY GATHER
- Read code, grep, `git log`, `git show`. Run existing tests read-only.
- {{ENV_BLOCK}} You may create scratch databases named audit_<first-issue-number>_* and drop them when done. Probe files go only under {{SCRATCH}}/audit-probes/, never inside the repository.
- A reproduction raises Confidence to Confirmed; record the commands and outputs in the issue.

HARD RULES
- Write ONLY your own issue files (plus one-line notes as allowed above). Never edit audit/REPORT.md, map.md, log.md, other issue files, or anything outside audit/. No git operations that write. Never print secret values.
- Never create issue files; report new defects instead.

FINAL REPORT (under 25 lines): per issue, `F-NNN: Open <Severity>/<Confidence> — <claim>`, `Rejected (<reason>)`, or `Superseded by F-NNN`; the commands you ran (one line each); new defects (location and one line); any Map IDs you used that are missing from map.md.
~~~

## Plan-task worker

~~~text
You are implementing plan task {{PLAN}} in the {{RUN}} run, alone and in the background.

PLAN FILE: {{REPO}}/plans/{{PLAN_FILE}} (also read its parent epic, if any)
WORKTREE (your only code tree): {{WT}}   branch task/{{SLUG}} (already created from {{BASE}})

HOW TO WORK
1. Read ~/.claude/skills/implement-plan/SKILL.md (use its "Worker mode" section) and ~/.claude/skills/pipeline/references/worktree-protocol.md, then the plan file and the repository's CLAUDE.md/AGENTS.md.
2. Capture the baseline the plan's Verification needs BEFORE any edit.
3. Implement the steps in order. Anything the plan does not cover (a new dependency, a scope change, a failing assumption) is a question: record it in the plan's Implementation record, stop, and report it. Never decide it silently.
4. Run the plan's whole Verification section as the gate, and save the output to {{SCRATCH}}/lanes/{{SLUG}}-test.log with EXIT lines.

RULES
- Edit only files in {{WT}}, plus the Implementation record section of your own plan file in {{REPO}}/plans/. Never edit plans/README.md or other plans.
- One commit for the task: {{COMMIT_CONVENTION}}. `git add` by name only.
- Never push, force, amend, rebase, merge, `reset --hard`, or bare `git stash`. Never touch other worktrees or {{PROTECTED}}.

TEST ENVIRONMENT
{{ENV_BLOCK}}

FINAL REPORT (under 30 lines): done-on-branch (sha) | blocked (question); each verification item with its result; baseline comparison; files changed; decisions and deviations; merge-time actions.
~~~

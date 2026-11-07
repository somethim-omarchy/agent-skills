---
name: job-hunt
description: Run a job search end to end by interviewing the user. Sets up a candidate profile and preferences, turns an existing CV into tailored per-track CVs (or builds one from questions), sweeps company job boards, aggregators and community boards (not just LinkedIn), scores and files matches per CV, and audits the GitHub and LinkedIn profiles. Use for "/job-hunt", "find me jobs", "set up my job search", "make my CVs", "new postings", "check my GitHub/LinkedIn for applying". Search and preparation only; applying and cover letters are the job-apply skill. Never applies or messages anyone.
argument-hint: "[setup | cv | search [track] | audit | status]"
---

# Job hunt

A method, not a person: everything about the candidate lives in the data folder and is collected by asking the user. Never invent facts about the candidate or a posting; when something is missing, ask.

## Data folder

`DATA` = `./Career/` relative to the directory the skill is called from (the session's working directory; if that directory is itself named `Career`, use it directly). Resolve it to an absolute path once at the start and use it everywhere below. If it does not exist, ask before creating it.

| Path | Holds | Written by |
|---|---|---|
| `DATA/profile.md` | Facts: contact, citizenship, languages, experience, education, projects, links, references, documents, words never to use | setup, cv |
| `DATA/preferences.md` | Tracks and levels, stacks, regions, visa rules, salary floors, start date, dealbreakers, application answers | setup, search feedback |
| `DATA/cvs/` | `<Name>_<Track>_CV.tex` per track + General, `Makefile`, `generated/*.pdf` | cv |
| `DATA/jobs/<track>/` | `README.md` (shortlist, read in full), `longlist.md` (everything that passed filters) | search |
| `DATA/jobs/contacts.md`, `DATA/jobs/tracker.md` | Public recruiter contacts; history of every posting seen | search |
| `DATA/applications/<slug>/` | Per-application materials | job-apply skill |

## Modes

`$ARGUMENTS` picks the mode. With no argument, run **status** and offer the next step.

### status
Read the data folder and report in one short table what exists and what is missing (profile fields, preferences answers, CVs per track, last search date, open applications). Recommend the next mode.

### setup (interview)
Follow `references/setup-interview.md`. Ask in small batches with AskUserQuestion (at most 4 questions per call, options plus free text), only for what is missing or stale. Write answers to `profile.md` / `preferences.md` immediately, with the date. Restate anything the user says that has consequences (for example a salary floor below a visa threshold) and record the warning next to it.

### cv
Follow `references/cv-workflow.md`: first look for an existing CV in `DATA` (`DATA/cvs/*.tex`, then any `*CV*`/`*cv*`/`*resume*` file in `DATA` as .tex, .pdf, .docx, .md or .txt); use the newest, and confirm with the user which one if there are several. Only if none is found, ask for one (path or pasted text). If there is one, read it fully and produce tailored variants per track in the same structure as `assets/cv-template.tex`. If there is none, build it from questions. Build PDFs with `make` in `DATA/cvs/` and check every PDF is the agreed page count with page breaks on section boundaries.

### search [track]
1. Read `preferences.md` (tracks, regions, visa rule, salary floors) and the CVs.
2. Sweep with `scripts/gather.py OUT.json` (company ATS boards, Arbeitnow, Let's Get Rusty, Sweden's Platsbanken, LaraJobs). Add company slugs to its board list as you discover them (Google `site:` searches in the user's browser are the fastest way, see `references/sources.md`). LinkedIn: user's own logged-in browser, read-only, a few searches; if a login or CAPTCHA appears, stop and ask the user to clear it.
3. Score with `scripts/score.py OUT.json SCORED.json`. The track keywords, stack weights and filters sit at the top of that script; on first run adapt them to the user's CVs and preferences (the shipped weights are for a web / DevOps / Rust candidate). Filters and scoring are documented in `references/scoring.md`; tell the user every filter if asked.
4. Read the best-scoring postings in full (ATS JSON, the posting page, or a detail fetch), then write `DATA/jobs/<track>/README.md` (ranked: score, company, role, location, why it matches that CV, watch-outs, employer link) and `longlist.md` (all that passed). Prefer the employer's own link over an aggregator.
5. Report the funnel honestly (total, in a track, passed filters, read in full) so a small shortlist is never mistaken for a small market.

### audit
- GitHub (`gh api users/<login>`, repos, pinned items via GraphQL): profile README public, pins match the target tracks, descriptions/topics/licences, CI on pinned repos, links on the CV that 404 (private repos).
- LinkedIn (user's browser, read-only; never edit anything): headline, About, open-to-work locations/titles/employment types, experience vs CV, skills, projects, languages. Output a prioritised checklist; the user makes the changes.

## Rules
- No outward actions: no applications, no messages, no profile edits, no repository visibility changes. Draft; the user sends.
- Work-authorisation rules and salary thresholds change: quote them only from an official page opened in this session, with the link; otherwise label them "recalled, verify".
- Read `preferences.md` for the user's visa rule before filtering; never reject a job for a reason the user has overruled.
- Heavy commands (CV builds) follow the machine's shared heavy-job lock when the user's instructions require one.
- After setup, cv or search, update the user's memory notes only with durable facts (where the data lives, rules they set), not with job lists.

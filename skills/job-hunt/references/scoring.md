# Filters and scoring (as implemented in scripts/score.py)

Adapt the keyword lists and weights at the top of `score.py` to the user's tracks and CVs during the first search; keep this file in sync with the script.

## 1. Track (from the job title)
- **rust**: "Rust" in the title, or 2+ mentions in the description (unless the title says PHP/Java/.NET/C#).
- **devops**: DevOps, SRE, site reliability, platform/infrastructure/cloud/ops/release engineer, Kubernetes.
- **web**: backend, frontend, full-stack, web developer, software engineer/developer, product engineer, PHP, Laravel, Django, React, Next.js, TypeScript, Node; not embedded/firmware/mobile/data science/ML/QA/test.
- Anything else is outside the search.

## 2. Hard filters (any one rejects)
| Filter | Rejects when |
|---|---|
| Student | Title: intern, internship, working student, Werkstudent, Praktikum, thesis, trainee, apprentice, student, PhD |
| Level too high | Title: staff, principal, lead, head, director, manager, VP, chief, CTO, architect |
| Level too low (web, devops) | Title: junior, graduate, entry |
| Years | Lowest stated requirement above 8 (web), 6 (devops), 7 (rust) |
| German required | Fluent/native/C1 German, "gute/sehr gute Deutschkenntnisse", "verhandlungssicher", "fluency in German", ... |
| Swedish required | Fluent/native Swedish, "Swedish required", "svenska krav" |
| Language of the ad | Platsbanken ad mostly in Swedish; Arbeitnow m/w/d ad with no English in its opening |
| Stack (web) | Title names Java, Spring, .NET, C#, Kotlin, Ruby/Rails, Angular, Vue |
| C++-first (rust) | "Strong/expert C++" with fewer than 3 Rust mentions |
| Legal limits | A specific citizenship (EU, German, UK, US, ...) or a security clearance / ITAR, unless NATO citizens are explicitly accepted |
Not a filter by default (user rule): location, and "no visa sponsorship" / "must already live here". Those are flags. Check `preferences.md` before changing this.

## 3. Score (0-100, only for jobs that pass)
- **Stack**: weighted keyword hits against the track's CV (e.g. web: Laravel 12, PHP 8, React 7, Django 7; devops: Ansible 7, Docker 5, Kubernetes 5; rust: Rust 12, embedded-hal/Embassy 7, ROS 5), capped at 40, times 1.4.
- **Level**: 15 when stated years fit the track, else 8; senior titles capped (12 web/devops, 6 robotics/embedded Rust).
- **Location**: Germany 12, Sweden 11, other Europe 8, remote 7, North America 5, elsewhere 3 (set the order from `preferences.md`).
- **Language**: 10 if German is not mentioned, 7 if it is.
- **Visa**: +8 when sponsorship/relocation is stated in a non-negated sentence; -8 when "no sponsorship" or a residency requirement is stated.
- Flags only: defence (rank up if the user prefers defence), possible agency.
- The same role in several cities is merged into one entry.

## 4. Shortlist format (DATA/jobs/<track>/README.md)
`| # | Score | Company | Role | Location | Why it matches the CV | Watch out | Link |`, ranked, then a "Rejected in this pass" line naming notable rejections and why. Every shortlist row is read in full first; the longlist is keyword-scored only and says so.

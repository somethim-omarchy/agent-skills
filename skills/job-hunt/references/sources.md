# Sources, in sweep order

Endpoints and slugs below come from memory and have not been tested. On the first run, test each with one request, record the result in the "Verified" column of the health table at the bottom, and fix this file when a recipe is wrong. Respect robots.txt and rate limits (about 1 request per second per host); stop on 403/429 and report the source as failed.

## Tier 1: Employer ATS feeds (public JSON, no login, most reliable)
Most European tech and robotics companies host jobs on one of these. Loop over `companies.md` slugs, filter by title keywords from `scoring.md`, then by location.

| ATS | Recipe |
|---|---|
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/<slug>/jobs?content=true` |
| Lever | `https://api.lever.co/v0/postings/<slug>?mode=json` |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/<slug>` |
| Personio (very common in Germany) | `https://<slug>.jobs.personio.de/xml` (also `.personio.com`) |
| Recruitee | `https://<slug>.recruitee.com/api/offers/` |
| SmartRecruiters | `https://api.smartrecruiters.com/v1/companies/<slug>/postings` |
| Workable | `https://apply.workable.com/api/v1/widget/accounts/<slug>` |
| join.com, Teamtailor, BambooHR | no stable public feed: use the careers page or a `site:` search |

Finding a company's ATS: open its careers page and look at the apply-link domain, or search `"<company>" site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:personio.de`.

## Tier 2: Aggregators with Europe / visa focus
- Arbeitnow (free JSON API at `https://www.arbeitnow.com/api/job-board-api?page=N`; verified 2026-11-06; fields: title, company_name, location, remote, tags, job_types, description (HTML-escaped), created_at (unix), url). **No visa-sponsorship field.** It also carries UK, FR, CH, NL jobs on other subdomains, so filter on the `url` host (`arbeitnow.com/` = Germany). Descriptions are best matched with word boundaries: plain `rust` also matches "trust". Links are Arbeitnow's, not the employer's: resolve the real apply URL.
- Verified 2026-11-06: Greenhouse, Lever and Ashby feed URLs return 200 for real slugs (guessed slugs for the seed companies did not exist, so find slugs from search results first).
- Bundesagentur für Arbeit Jobbörse; Make it in Germany jobs portal (for foreign applicants).
- Relocate.me and Landing.jobs (visa/relocation-focused tech roles in Europe).
- Welcome to the Jungle, Wellfound, Honeypot-style boards; Germantechjobs; Berlin Startup Jobs; StepStone, Xing, Indeed.de (large but noisy; use as a coverage check, not the primary source).
- Remote boards (only for the `remote` region rule): RemoteOK, We Work Remotely, Remotive, Himalayas, Jobicy.
- Paid scrapers (e.g. the `apify-job-boards` skill) are optional and cost money: never use them without telling the user the estimated cost first.

## Tier 3: Open-web search with `site:` dorks (the "everywhere" layer)
Use WebSearch with queries like these, one tier of region at a time:
- `site:jobs.lever.co OR site:boards.greenhouse.io OR site:jobs.ashbyhq.com "robotics" "software engineer" Germany`
- `site:personio.de "Rust" Entwickler OR Engineer`
- `"Rust" "embedded" "visa sponsorship" Germany software engineer`
- `"ROS 2" "software engineer" Munich OR Stuttgart OR Berlin OR Nuremberg OR Dresden`
- Same patterns for US, Canada, Netherlands, Estonia, Switzerland, with "visa sponsorship" or "relocation".
Rerun with German titles: `Softwareentwickler Rust`, `Robotik Softwareingenieur`, `Embedded Entwickler`.

## Tier 4: Community and curated threads
- Hacker News "Ask HN: Who is hiring?" (monthly thread; search with the HN Algolia API, filter Europe/visa/remote).
- r/rust "Who's Hiring" monthly thread; This Week in Rust jobs section; rustjobs.dev.
- ROS Discourse "Jobs" category (discourse.ros.org); PX4/Dronecode and Auterion community pages.
- Company engineering blogs and "we're hiring" posts in robotics newsletters.

## Tier 5: Browser (last resort, Claude in Chrome)
LinkedIn, Indeed, Glassdoor and sites without feeds. User's own session, low volume (a handful of queries, first 2 pages), no bulk scraping, no automation of logins. If the site shows a CAPTCHA or login wall, stop and report. Close tabs opened.

## Company seed list (`companies.md`)
Create `DATA/jobs/companies.md` (DATA = ./Career from the call path) on first run from the list below. These are names from memory, not verified as hiring or as having the listed ATS. Fill slugs and region on first run; delete companies that no longer exist. Add every new company found in Tiers 2-4 so the Tier 1 sweep grows over time.

- Germany robotics / autonomy: Neura Robotics, Agile Robots, Franka Robotics, RobCo, Wandelbots, Sereact, ARX Robotics, Magazino, Kinexon, Vay, Quantum Systems, Helsing (defense), Stark (defense), Isar Aerospace, Volocopter.
- Rust-forward: Ferrous Systems, Embark Studios, Rerun (Sweden, used in Arbi's projects), Tweede golf (NL), Oxide (US), 1Password (Canada).
- Other Europe robotics / drones: ANYbotics (CH), Starship Technologies (EE), Auterion (CH/US), Nomagic (PL).
- Overseas: Skydio, Zipline, Anduril, Applied Intuition, Clearpath/OTTO (Rockwell, Canada), Kinova (Canada).
- Large industrial / automotive: KUKA, Bosch, Siemens, ZF, Mercedes-Benz, BMW, Continental; high volume, often C++ and German heavy.

## Source health table (fill on each run)
| Source | Verified | Last run | Raw | Kept | Notes |
|---|---|---|---|---|---|

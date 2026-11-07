# CV workflow

## Intake
1. Look in `DATA` first: `DATA/cvs/*.tex`, then any file in `DATA` whose name contains CV, cv, Lebenslauf or resume (.tex, .pdf, .docx, .md, .txt). Several found: list them and ask which is current. None found: ask "Do you have a current CV? Give me the file path or paste it." Accept LaTeX, PDF (read it), DOCX or plain text.
2. Back up any existing CV source before changing it (dated copy next to it or in a backup folder the user names).

## With an existing CV
1. Read it completely. List every fact (roles, dates, employers, bullets, numbers, projects, links, skills, education, languages) in your notes; these are the only facts you may use, plus facts from the user's public projects that you have read yourself (repo READMEs, project pages), which you name to the user.
2. Confirm the tracks from `preferences.md` (setup). Produce one General CV and one CV per track, all in the structure of `assets/cv-template.tex` (or the user's existing LaTeX layout if they have one):
   - Headline under the name naming the track's role and stack.
   - Summary rewritten for the track.
   - Section order chosen by where the evidence is: experience first when employment matches the track; projects first when the track's proof is in personal or open-source work.
   - Bullets reordered and reworded toward the track; drop or shorten what is irrelevant; never add a claim that is not in the facts list.
   - Skills grouped for the track.
3. Keep invariants the user has (page count, entry format, date format). Default: 2 pages, page break on a section or company boundary.
4. Put files in `DATA/cvs/` as `<Name>_<Track>_CV.tex`; copy `assets/Makefile` and set the CV list; build; check page counts and page breaks with `pdfinfo`/`pdftotext`; look at a low-resolution render of each page.
5. Show the user a table: per CV, the headline, what leads, and what changed. Flag every new fact you added from their public work so they can veto it.

## Without a CV
Ask, in batches: contact block; each job (title, employer, dates, employment type, 2-5 achievements with numbers); projects (name, link, what it does, stack, a number); education; certifications/courses; skills; languages. Then follow the steps above from step 2.

## Later edits
Any change: back up, edit, rebuild, re-check page count and breaks, report what changed.

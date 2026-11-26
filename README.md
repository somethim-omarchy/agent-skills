# Agent skills

Every user-level Claude Code and Codex skill in one place. `./install.sh` symlinks each skill into `~/.claude/skills` (Claude Code) and `~/.agents/skills` (Codex), so editing an installed skill edits this checkout: commit and push from here. Whatever was already at a destination, including an old copy in `~/.codex/skills`, is moved to `~/.local/state/agent-skills/backup-<time>/`. The omarchy-dotfiles bootstrap clones this repository to `~/Projects/omarchy/agent-skills` and runs the installer.

| Folder | Contents |
| --- | --- |
| `skills/` | My own skills: `audit-codebase`, `discover-and-plan`, `fix-audit-findings`, `implement-plan`, `pipeline`, `job-hunt`, `job-apply`, `tutor` |
| `vendor/` | Third-party skills kept as installed: the caveman family (`caveman*`, `cavecrew`, `megacave`, `ultracave`, from [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)), `hallmark` (MIT, see its `LICENSE`), `find-skills`, `investigate-first`, `lean-build`, `migration`, `safe-refactor`, `surgical-patch`, `verify-and-stop` |

Not kept here:
- Skills Omarchy ships (`omarchy`, `omarchy-app`, `diagnose-crash`) are links into `/usr/share/omarchy` and follow the installed version.
- Skills synced from claude.ai and plugin-provided skills come from their own installations.
- Project skills stay committed in their projects: `translations` (synis-ai, basilic), the Laravel Boost skills (zennstream), `latchkey-basics` and `latchkey-porting` (shipped with the latchkey crate).

To add a skill, put its folder (with `SKILL.md` at its root) in `skills/` or `vendor/` and rerun `./install.sh`. Test the installer with `tests/test_install.sh`.

This repository includes personal contact details (`skills/job-hunt/assets/cv-template.tex`); keep it private.

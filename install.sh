#!/usr/bin/env bash
# Links every skill in skills/ and vendor/ into the agents' user skill folders.
# Claude Code reads ~/.claude/skills; Codex reads ~/.agents/skills. Links point
# back into this checkout, so editing an installed skill edits the repository.
# Anything already at a destination is moved to a timestamped backup first.
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
claude_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
agents_dir="$HOME/.agents/skills"
codex_dir="${CODEX_HOME:-$HOME/.codex}/skills"
backup_dir="${XDG_STATE_HOME:-$HOME/.local/state}/agent-skills/backup-$(date +%Y%m%d-%H%M%S)"

backup() { # path, label
  mkdir -p "$backup_dir/$2"
  mv "$1" "$backup_dir/$2/"
}

mkdir -p "$claude_dir" "$agents_dir"
linked=0
for source in "$repo_dir"/skills/*/ "$repo_dir"/vendor/*/; do
  source="${source%/}"
  name="${source##*/}"
  [[ -f "$source/SKILL.md" ]] || { echo "Missing SKILL.md: $source" >&2; exit 1; }
  for target_dir in "$claude_dir" "$agents_dir"; do
    target="$target_dir/$name"
    [[ -L "$target" && "$(readlink "$target")" == "$source" ]] && continue
    if [[ -e "$target" || -L "$target" ]]; then backup "$target" "${target_dir//\//_}"; fi
    ln -s "$source" "$target"
    linked=$((linked + 1))
  done
  # Codex also reads its legacy folder; an old copy there would load twice.
  if [[ -e "$codex_dir/$name" || -L "$codex_dir/$name" ]]; then backup "$codex_dir/$name" codex; fi
done

echo "Linked $linked skill destinations from $repo_dir."
[[ -d "$backup_dir" ]] && echo "Replaced copies are in $backup_dir."
exit 0

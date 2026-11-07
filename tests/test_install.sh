#!/usr/bin/env bash
# Runs install.sh against a throwaway HOME and checks links, backups and reruns.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
home="$(mktemp -d)"
trap 'rm -rf "$home"' EXIT
run() { env -u CLAUDE_CONFIG_DIR -u CODEX_HOME -u XDG_STATE_HOME HOME="$home" "$repo_dir/install.sh" >/dev/null; }
fail() { echo "FAIL: $*" >&2; exit 1; }

mkdir -p "$home/.claude/skills/pipeline" "$home/.codex/skills/pipeline" "$home/.claude/skills/keep-me"
echo old >"$home/.claude/skills/pipeline/SKILL.md"
run

for dir in .claude/skills .agents/skills; do
  for source in "$repo_dir"/skills/*/ "$repo_dir"/vendor/*/; do
    source="${source%/}"
    [[ "$(readlink "$home/$dir/${source##*/}")" == "$source" ]] || fail "$dir/${source##*/} not linked"
  done
done
[[ -d "$home/.claude/skills/keep-me" ]] || fail "unrelated skill removed"
[[ ! -e "$home/.codex/skills/pipeline" ]] || fail "legacy Codex copy left in place"
grep -rqx old "$home/.local/state/agent-skills" || fail "replaced copy not backed up"

backups="$(find "$home/.local/state/agent-skills" -mindepth 1 -maxdepth 1 | wc -l)"
sleep 1
run
[[ "$(find "$home/.local/state/agent-skills" -mindepth 1 -maxdepth 1 | wc -l)" == "$backups" ]] || fail "rerun made a new backup"
echo "PASS"

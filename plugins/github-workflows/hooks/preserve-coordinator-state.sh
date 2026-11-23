#!/usr/bin/env bash
# PreCompact hook: feeds a coordinator's run-state file into the compaction.
#
# The github-epic-to-merged-prs and github-issue-burndown skills keep their state in
# "$(git rev-parse --git-common-dir)/coordinator/<name>.md". Claude Code appends this
# script's stdout to the compaction instructions, so the summary keeps that state.
#
# Never blocks the compaction: always exits 0, and prints nothing outside a repo, with no
# git, or with no state files. Output is capped at MAX_FILES files of MAX_BYTES bytes each, and at MAX_TOTAL bytes overall, under the 10,000 characters Claude Code allows a hook.

MAX_FILES=3
MAX_BYTES=3000
MAX_TOTAL=9500   # hard cap on all output; Claude Code allows a hook 10,000 characters

main() {
    local input cwd common dir f
    input=$(cat 2>/dev/null) || input=
    cwd=
    if command -v jq >/dev/null 2>&1; then
        cwd=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null) || cwd=
    fi
    [ -n "$cwd" ] || cwd=$PWD
    [ -d "$cwd" ] || return 0
    command -v git >/dev/null 2>&1 || return 0
    common=$(git -C "$cwd" rev-parse --git-common-dir 2>/dev/null) || return 0
    [ -n "$common" ] || return 0
    case $common in /*) ;; *) common=$cwd/$common ;; esac
    dir=$common/coordinator
    [ -d "$dir" ] || return 0

    local files=()
    while IFS= read -r f; do
        [ -n "$f" ] && files+=("$f")
    done < <(ls -t -- "$dir"/*.md 2>/dev/null | head -n "$MAX_FILES")
    [ "${#files[@]}" -gt 0 ] || return 0

    printf '%s\n' "Preserve this coordinator run state verbatim in the summary: agent ids, PRs, review rounds, models and escalation triggers, and next actions. Resume the skill from this file after compacting."
    for f in "${files[@]}"; do
        printf '\n--- %s ---\n' "$f"
        head -c "$MAX_BYTES" -- "$f" 2>/dev/null
        printf '\n'
    done
}

main 2>/dev/null | head -c "$MAX_TOTAL"
exit 0

#!/usr/bin/env bash
# Wait for a Brooke review on the PR's CURRENT head SHA. Run it in the
# background (run_in_background), never as a foreground sleep.
#
# Usage: wait-brooke.sh <owner/repo> <pr> [--request]
#   --request  post "/prrb" right away (use after pushing review fixes:
#              Brooke does not re-review on push).
#
# Last line of output, and exit code:
#   REVIEWED <review-id> <sha>   0  a Brooke review exists on the head
#   STALE <sha>                  3  branch is behind its base; Brooke skips it
#   NO_REVIEW <sha>              2  no review after 3 /prrb nudges
#   ERROR <message>              1
set -uo pipefail

repo=${1:?usage: wait-brooke.sh <owner/repo> <pr> [--request]}
pr=${2:?usage: wait-brooke.sh <owner/repo> <pr> [--request]}
request=${3:-}
bot=brooke-reviews
max_nudges=3
nudge_after=300   # Brooke takes at most ~5 minutes
first_check=90    # no eyes reaction by now means she missed the request

nudges=0
prrb() {
    if ! gh pr comment "$pr" -R "$repo" --body "/prrb" >/dev/null; then
        echo "ERROR could not post /prrb"; exit 1
    fi
    nudges=$((nudges + 1)); last_nudge=$(date +%s)
}

start=$(date +%s); last_nudge=$start
pending_request=
[ "$request" = "--request" ] && pending_request=1   # posted after the stale check below

while :; do
    head=$(gh api "repos/$repo/pulls/$pr" --jq .head.sha) || { echo "ERROR cannot read PR"; exit 1; }
    id=$(gh api --paginate "repos/$repo/pulls/$pr/reviews" \
        --jq ".[] | select(.user.login | startswith(\"$bot\")) | select(.commit_id == \"$head\") | .id" | tail -1)
    if [ -n "$id" ]; then echo "REVIEWED $id $head"; exit 0; fi

    # Brooke refuses a branch behind its base. GitHub reports BEHIND only
    # when the base requires up-to-date branches; otherwise a stale PR shows
    # CLEAN. So ask the compare API how far behind the head is.
    state=$(gh pr view "$pr" -R "$repo" --json mergeStateStatus --jq .mergeStateStatus)
    base=$(gh api "repos/$repo/pulls/$pr" --jq .base.ref)
    behind=$(gh api "repos/$repo/compare/$base...$head" --jq .behind_by 2>/dev/null || echo 0)
    if [ "$state" = BEHIND ] || [ "$state" = DIRTY ] || [ "${behind:-0}" -gt 0 ]; then
        echo "STALE $head ($state, $behind behind $base)"; exit 3
    fi
    if [ -n "$pending_request" ]; then prrb; pending_request=; fi

    now=$(date +%s)
    # The PR just opened and no /prrb was posted: check she saw it.
    if [ "$nudges" = 0 ] && [ $((now - start)) -ge "$first_check" ]; then
        eyes=$(gh api "repos/$repo/issues/$pr/reactions" \
            --jq "[.[] | select(.content == \"eyes\") | select(.user.login | startswith(\"$bot\"))] | length")
        [ "$eyes" = 0 ] && prrb
    fi
    if [ $((now - last_nudge)) -ge "$nudge_after" ]; then
        if [ "$nudges" -ge "$max_nudges" ]; then echo "NO_REVIEW $head"; exit 2; fi
        prrb
    fi
    sleep 30
done

#!/usr/bin/env bash
# Did Brooke's latest review on the PR's CURRENT head sink the score over a
# security problem? That is one of the three triggers for moving a PR from a
# Sonnet implementer to an Opus one (the others are two review rounds and two CI
# failures).
#
# Usage: brooke-security.sh <owner/repo> <pr> [threshold]   (threshold default 80)
# Env:   REVIEW_ID=<id>  check that review instead of the latest on the head (for testing).
#
# Last line of output, and exit code:
#   ESCALATE <score> <review-id>   0  score < threshold AND the review's
#                                     "### Security" section has a "**Blocking:**" item
#   NO <score> <review-id>         1  anything else (including a clean Security section)
#   NONE                           3  no Brooke review on the head yet
#   ERROR <message>                2
set -uo pipefail

repo=${1:?usage: brooke-security.sh <owner/repo> <pr> [threshold]}
pr=${2:?usage: brooke-security.sh <owner/repo> <pr> [threshold]}
threshold=${3:-80}
bot=brooke-reviews

head=$(gh api "repos/$repo/pulls/$pr" --jq .head.sha) || { echo "ERROR cannot read PR"; exit 2; }
if [ -n "${REVIEW_ID:-}" ]; then
    review=$(gh api "repos/$repo/pulls/$pr/reviews/$REVIEW_ID" --jq '{id, body}') || { echo "ERROR cannot read review"; exit 2; }
else
review=$(gh api --paginate "repos/$repo/pulls/$pr/reviews" \
    --jq ".[] | select(.user.login | startswith(\"$bot\")) | select(.commit_id == \"$head\") | {id, body}" \
    | jq -s 'last // empty') || { echo "ERROR cannot read reviews"; exit 2; }
fi
[ -n "$review" ] || { echo "NONE"; exit 3; }

id=$(jq -r .id <<<"$review")
body=$(jq -r .body <<<"$review")
score=$(grep -oE '\*\*Quality score:\*\* *[0-9]+' <<<"$body" | grep -oE '[0-9]+$' | head -1)
# The Security section runs from its heading to the next "### " heading.
security=$(awk '/^### Security/{on=1; next} /^### /{on=0} on' <<<"$body")

if [ -n "$score" ] && [ "$score" -lt "$threshold" ] && grep -q '\*\*Blocking:\*\*' <<<"$security"; then
    echo "ESCALATE $score $id"; exit 0
fi
echo "NO ${score:-?} $id"; exit 1

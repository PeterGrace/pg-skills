#!/usr/bin/env bash
# Is Brooke OK with the PR as it stands? Exit 0 only when the latest
# Brooke review on the CURRENT head SHA has no inline comments and its
# body does not ask for changes. Prints the verdict, score and reason.
#
# Usage: brooke-ok.sh <owner/repo> <pr>
set -uo pipefail

repo=${1:?usage: brooke-ok.sh <owner/repo> <pr>}
pr=${2:?usage: brooke-ok.sh <owner/repo> <pr>}
bot=brooke-reviews

head=$(gh api "repos/$repo/pulls/$pr" --jq .head.sha) || { echo "ERROR cannot read PR"; exit 1; }
review=$(gh api --paginate "repos/$repo/pulls/$pr/reviews" \
    --jq ".[] | select(.user.login | startswith(\"$bot\")) | select(.commit_id == \"$head\") | [.id, .submitted_at] | @tsv" |
    sort -k2 | tail -1 | cut -f1)
if [ -z "$review" ]; then echo "NOT_OK no Brooke review on head $head"; exit 1; fi

body=$(gh api "repos/$repo/pulls/$pr/reviews/$review" --jq .body)
score=$(grep -oE 'Quality score:\*\* *[0-9]+' <<<"$body" | grep -oE '[0-9]+$' || echo "?")
inline=$(gh api --paginate "repos/$repo/pulls/$pr/reviews/$review/comments" --jq '.[].id' | wc -l)

if [ "$inline" -gt 0 ]; then
    echo "NOT_OK review $review on $head: $inline inline comment(s), score $score"; exit 1
fi
if grep -qiE 'request(s|ed)? changes|needs? (two |a few |several )?corrections? before merg' <<<"$body"; then
    echo "NOT_OK review $review on $head: body asks for changes, score $score"; exit 1
fi
echo "OK review $review on $head: no inline comments, score $score"

#!/usr/bin/env bash
# Merge the PR only if every condition holds; otherwise refuse and say why.
# Never bypass this with a bare `gh pr merge`.
#
# Usage: merge-if-ready.sh <owner/repo> <pr> [--merge|--squash|--rebase] [--dry-run]
# Env:   ALLOW_NO_CHECKS=1  accept a repo with no CI checks at all.
set -uo pipefail

repo=${1:?usage: merge-if-ready.sh <owner/repo> <pr> [strategy] [--dry-run]}
pr=${2:?}
shift 2
strategy=--merge; dry=
for a in "$@"; do
    case $a in --merge|--squash|--rebase) strategy=$a ;; --dry-run) dry=1 ;; esac
done
here=$(dirname "$(readlink -f "$0")")
fail() { echo "REFUSED: $*"; exit 1; }

owner=${repo%/*}; name=${repo#*/}
default=$(gh repo view "$repo" --json defaultBranchRef --jq .defaultBranchRef.name)
read -r base head_ref head_sha state < <(gh api "repos/$repo/pulls/$pr" \
    --jq '[.base.ref, .head.ref, .head.sha, .state] | @tsv')

[ "$state" = open ] || fail "PR is $state"
[ "$base" = "$default" ] || fail "base is $base, not $default"

remote_sha=$(git ls-remote "https://github.com/$repo.git" "refs/heads/$head_ref" | cut -f1)
[ "$remote_sha" = "$head_sha" ] || fail "PR head $head_sha != branch tip $remote_sha (GitHub stale; wait or push an empty commit)"

"$here/brooke-ok.sh" "$repo" "$pr" || fail "Brooke is not OK on the current head"

unreplied=$(gh api graphql -F owner="$owner" -F name="$name" -F pr="$pr" -f query='
  query($owner:String!,$name:String!,$pr:Int!){repository(owner:$owner,name:$name){
    pullRequest(number:$pr){reviewThreads(first:100){nodes{
      comments(first:100){nodes{author{login}}}}}}}}' \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[]
         | select(.comments.nodes[0].author.login | startswith("brooke-reviews"))
         | select([.comments.nodes[].author.login | select(startswith("brooke-reviews") | not)] | length == 0)]
        | length')
[ "$unreplied" = 0 ] || fail "$unreplied Brooke review thread(s) have no reply"

checks=$(gh pr checks "$pr" -R "$repo" --json state --jq '[.[].state] | group_by(.) | map("\(.[0])=\(length)") | join(" ")' 2>/dev/null)
if [ -z "$checks" ]; then
    [ "${ALLOW_NO_CHECKS:-}" = 1 ] || fail "no CI checks reported (set ALLOW_NO_CHECKS=1 if the repo has none)"
else
    bad=$(gh pr checks "$pr" -R "$repo" --json state \
        --jq '[.[] | select(.state != "SUCCESS" and .state != "SKIPPED" and .state != "NEUTRAL")] | length')
    [ "$bad" = 0 ] || fail "CI not green: $checks (cancelled/flaky runs: gh run rerun <run> --failed)"
fi

mss=$(gh pr view "$pr" -R "$repo" --json mergeStateStatus --jq .mergeStateStatus)
[ "$mss" = CLEAN ] || fail "mergeStateStatus is $mss"

if [ -n "$dry" ]; then echo "READY (dry run): would gh pr merge $pr $strategy"; exit 0; fi
# Pin the merge to the head every check above inspected: GitHub refuses it
# if anything was pushed in between.
gh pr merge "$pr" -R "$repo" "$strategy" --match-head-commit "$head_sha" &&
    echo "MERGED $pr ($strategy) at $head_sha"

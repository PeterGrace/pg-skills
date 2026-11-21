#!/usr/bin/env bash
# Print the highest-priority, then oldest, open issue that is ready for the
# burndown, or nothing.
#
# Usage: next-issue.sh <owner/repo> [label] [blocked-label]
#        next-issue.sh --list <owner/repo> [label] [blocked-label]
#   --list  print every candidate in pick order with its rank and where the
#           rank came from (skips only the open-PR check), for reporting.
#
# Eligible: open, carries <label> (default "accepted"), does not carry
# <blocked-label> (default "burndown-blocked"), is not an epic (has
# sub-issues), is unassigned or assigned to the gh user, and has no open
# pull request that would close it. Prints "<number>\t<title>\t<rank>\t<source>".
#
# Priority comes from GitHub's native issue field named "Priority" (org
# issue fields: Urgent / High / Medium / Low) and from priority labels.
# The higher of the two wins. Only the field named "Priority" counts: other
# fields such as "Effort" also have a "High" option.
#   0  urgent | critical | blocker | highest | p0 | sev0 | s0
#   1  high | p1 | sev1 | s1
#   2  medium | normal | p2 | sev2 | s2      (also: no priority at all)
#   3  low | p3 | sev3 | s3
#   4  lowest | p4 | sev4 | s4
# Labels may carry a "priority"/"prio"/"pri" prefix or suffix: "priority: high",
# "priority/high", "prio-high", "high-priority", "high priority". Ties go oldest first (lowest number).
set -euo pipefail

list=
if [ "${1:-}" = --list ]; then list=1; shift; fi
repo=${1:?usage: next-issue.sh [--list] <owner/repo> [label] [blocked-label]}
label=${2:-accepted}
blocked=${3:-burndown-blocked}
me=$(gh api user --jq .login)

# The REST list (unlike `gh issue list --json`) carries issue_field_values
# and sub_issues_summary. --paginate emits one array per page; --jq runs on
# each page, so ranking happens per issue and sorting happens below.
jq_rank='
  def prio:
    ascii_downcase | sub("^(priority|prio|pri)[:/ _-]*"; "") | sub("[:/ _-]*(priority|prio|pri)$"; "") |
    if   test("^(p0|sev-?0|s0|critical|urgent|blocker|highest)$") then 0
    elif test("^(p1|sev-?1|s1|high)$")                            then 1
    elif test("^(p2|sev-?2|s2|medium|normal)$")                   then 2
    elif test("^(p3|sev-?3|s3|low)$")                             then 3
    elif test("^(p4|sev-?4|s4|lowest)$")                          then 4
    else null end;
  def field_rank:
    [(.issue_field_values // [])[]
     | select((.issue_field_name // "") | ascii_downcase == "priority")
     | (.single_select_option.name // "") | prio | select(. != null)] | min;
  def label_rank: [.labels[].name | prio | select(. != null)] | min;'

candidates=$(gh api --paginate \
    "repos/$repo/issues?state=open&labels=$(printf %s "$label" | jq -sRr @uri)&per_page=100" \
    --jq "$jq_rank
          .[]
          | select(.pull_request | not)
          | select([.labels[].name] | index(\"$blocked\") | not)
          | select((.assignees | length) == 0 or ([.assignees[].login] | index(\"$me\")))
          | select((.sub_issues_summary.total // 0) == 0)
          | field_rank as \$f | label_rank as \$l
          | ([\$f, \$l] | map(select(. != null)) | min // 2) as \$r
          | (if \$f != null and \$f == \$r then \"field\" elif \$l != null then \"label\" else \"default\" end) as \$src
          | [\$r, .number, .title, \$src] | @tsv" |
    sort -t$'\t' -k1,1n -k2,2n |
    awk -F'\t' -v OFS='\t' '{print $2, $3, $1, $4}')

if [ -n "$list" ]; then printf '%s\n' "$candidates"; exit 0; fi

# Work in progress elsewhere: every session runs as the same gh user, so
# self-assignment can't tell sessions apart. A branch or worktree named for
# the issue (`*issue-<N>-*`, the naming every flow here uses) means another
# session owns it. Remote heads come from the API; local branches and
# worktrees only when run inside the repo's checkout.
remote_heads=$(gh api --paginate "repos/$repo/git/matching-refs/heads/" --jq '.[].ref' 2>/dev/null || true)
local_heads=
if git rev-parse --git-dir >/dev/null 2>&1; then
    local_heads=$(git for-each-ref --format='%(refname)' refs/heads; git worktree list --porcelain | grep '^worktree ')
fi
in_progress() { printf '%s\n%s\n' "$remote_heads" "$local_heads" | grep -qE "issue-$1(-|$)"; }

printf '%s\n' "$candidates" |
while IFS=$'\t' read -r n title rank src; do
    [ -n "$n" ] || continue
    if in_progress "$n"; then echo "skip #$n: a branch or worktree for it exists" >&2; continue; fi
    # The list endpoint lags: an issue closed seconds ago can still be listed
    # as open. Re-check the one we would pick.
    [ "$(gh issue view "$n" -R "$repo" --json state --jq .state)" = OPEN ] || continue
    open_prs=$(gh issue view "$n" -R "$repo" --json closedByPullRequestsReferences \
        --jq '.closedByPullRequestsReferences[].number' |
        while read -r p; do
            # `if`, not `[ ] && echo`: a false test as the loop's last command
            # would fail the pipeline and, under set -e, end the script.
            if [ "$(gh pr view "$p" -R "$repo" --json state --jq .state)" = OPEN ]; then echo "$p"; fi
        done) || true
    [ -z "$open_prs" ] || continue
    printf '%s\t%s\t%s\t%s\n' "$n" "$title" "$rank" "$src"
    break
done

---
name: github-epic-to-merged-prs
description: "Use when a GitHub epic, milestone or plan is broken into several sub-issues and the user wants them carried through to merged PRs by background subagents, one issue each in its own worktree, with each PR reviewed by a person or review bot, the review answered, and the PR merged into a milestone integration branch that lands on main in one final merge. Triggers on \"run the sub-issues with subagents\", \"execute epic N\", \"work through milestone N's issues\", \"fan out the issues\", \"take each sub-issue to a PR\", or \"keep going the way we did before\" after this flow has been used."
---

# GitHub Epic → Merged PRs (subagent coordinator)

You coordinate and the subagents implement. Each sub-issue gets its own
background agent, its own git worktree and its own PR. The PRs merge into a
**milestone integration branch**, not `main`; `main` gets the whole milestone
in one final merge once it is complete, so `main` stays free for production
hotfixes in the meantime. Your job is to choose
what runs next, write each agent's brief, watch for reviews and CI, tell the
agent to answer its review, merge and clean up. Don't write the feature code
yourself.

The canonical write-up is the catalog concept `/processes/subagent-pr-workflow.md`
in catalog `peter-grace` on the Telekin server. Read it, along with the project's own concept
(for its reviewer bot, gates and quirks), before starting.

**REQUIRED SUB-SKILLS** (the agents run them, not you): `github-issue-to-pr`,
`github-address-pr-review`. Upstream of this skill: a checked-in plan, then
`github-issue-to-subissues` on the epic, which needs the user's acceptance.

## Before the first agent

1. **The issues exist.** Run `gh api repos/{owner}/{repo}/issues/<epic>/sub_issues`
   and, for each issue, `.../issues/<N>/dependencies/blocked_by`. If there are
   no sub-issues, run `github-issue-to-subissues` first.
2. **The reviewer.** Find out who reviews: from the project's catalog concept,
   or from `gh api .../pulls/<recent>/reviews --jq '.[].user.login'` on a
   recently merged PR. Bots log in with a `[bot]` suffix, for example
   `brooke-reviews[bot]`, so match with `startswith(...)`. If there's no
   reviewer, ask the user whether to merge without a review.
3. **Merge authorization.** Merge only if the user has explicitly said you
   may merge in this project. Record the conditions they gave in the catalog
   and in memory. If they haven't, don't merge: run the flow up to "review
   addressed, CI green", then report each PR as ready for them to merge.
   A standing merge authorization covers sub-issue PRs into the milestone
   branch. The final merge into `main` needs the user's go-ahead at that time,
   unless they've said explicitly that the standing authorization covers it.
4. **The gates.** Find the project's lint and test commands in its justfile,
   Makefile or CLAUDE.md. Every agent must pass them before it pushes.
5. **The milestone branch.** Name it `milestone/<epic>-<slug>`. If the epic
   or the catalog already names one, reuse it. Otherwise cut it from
   `origin/main` after the plan PR has merged, and push it:
   ```bash
   git fetch origin && git push origin origin/main:refs/heads/milestone/<epic>-<slug>
   ```
   Put its name in a comment on the epic, and in every brief.
6. **CI and the reviewer cover PRs into it.** Check that CI runs on pull
   requests into a non-default base: in `.github/workflows/*.yml`, an
   `on.pull_request.branches` filter listing only `main` skips them. Also
   check that the reviewer bot reviews PRs whose base isn't the default
   branch (the project's catalog concept, or the first PR's reviews). If
   either doesn't, stop and ask the user: changing CI config is a repo
   change, and merging unreviewed or untested isn't the deal. Note any
   branch protection on `main` that the final merge must satisfy.

## The loop

Repeat until every sub-issue is merged into the milestone branch. Below,
`<M>` is the milestone branch.

1. **Pick the ready issues.** An issue is ready when all its blockers have
   merged. Start them in parallel only if they touch different files.
   Serialize the ones that would conflict; the plan's Files lists tell you
   which.
2. **Create a worktree.** Run
   `git worktree add .worktrees/<repo>-<N> -b <type>-issue-<N>-<slug> origin/<M>`
   after a `git fetch`. Never reuse another agent's worktree.
3. **Start the agent in the background** with the brief below, using
   `subagent_type: "github-workflows:issue-implementer"` on the Agent call. Never use
   `general-purpose`, `claude` or a fork for this. Keep its agent id, because
   the same agent must answer the review.
   `issue-implementer` (`agents/issue-implementer.md` in this plugin) runs on
   Sonnet by default and already holds the standing rules: the workflow,
   worktree and git discipline, gates, shared-machine hygiene, attribution
   and the report format. **Always start on Sonnet: leave `model` off the
   call.** The plan and the gates carry most of the judgment. Opus is only
   for taking over a PR, never a first attempt, however subtle the
   sub-issue looks. In the week to 2026-11-21, 58 of 117 implementers ran on
   Opus at about 4× the cost, most with no stated reason. See **Escalating
   to Opus**.
4. **Watch the review** in a background shell (`run_in_background`), never a
   foreground sleep. Use the first of these that exists, and write your own
   loop only when none does:
   1. **The repo's watcher.** If the repo ships agent tooling (okf_mcp:
      `tools/agentic/watch-review.sh <P>`), use it, and act on its exit code
      (re-trigger, stale branch, round cap, timeout). Don't write a loop to
      do its job: these repos have a hook that refuses one. Their other
      scripts work the same way: `gate.sh` for gates, `merge-reviewed.sh`
      for merges.
   2. **This plugin's watcher**, for a Brooke review:
      `${CLAUDE_SKILL_DIR}/../github-issue-burndown/scripts/wait-brooke.sh O/R P`
      (add `--request` after a push). It waits for a review on the current
      head, re-triggers on its own, and exits `NO_REVIEW` or `STALE` instead
      of waiting forever.
   3. **Your own loop, as a last resort.** Only when the repo has no watcher
      and the reviewer isn't Brooke. Give it a deadline and make it say so
      when the deadline passes:
      ```bash
      HEAD_SHA=$(gh api repos/O/R/pulls/P --jq .head.sha) && [ -n "$HEAD_SHA" ] \
        || { echo "ERROR could not read the head of P"; exit 1; }
      end=$(( $(date +%s) + 600 ))
      until [ -n "$(gh api --paginate repos/O/R/pulls/P/reviews --jq ".[]|select((.user.login|startswith(\"REVIEWER\")) and .commit_id==\"$HEAD_SHA\")|.id")" ]; do
        [ "$(date +%s)" -ge "$end" ] && { echo "NO_REVIEW P after 10 min"; exit 2; }
        sleep 60
      done; echo "reviewed P"
      ```
      Match the current head's SHA, not any review: an earlier round's
      review would end the wait at once. Read every page (`--paginate`):
      GitHub returns 30 reviews per page, so on a long-running PR the
      current head's review can be on a later page. The `--jq` filter runs
      once per page and prints one id per match, so test whether it printed
      anything. Don't count per page, and don't use `--slurp`, which `gh`
      refuses alongside `--jq`. When it exits `NO_REVIEW`, go to
      step 5 straight away. Your next wake-up is the watcher exiting, so a
      watcher without a deadline can leave the whole run waiting for hours.
5. **If no review arrives,** first read the reviewer's *issue comments* on the
   PR. Bots often explain a skip there, for example "out of date with main".
   - If the branch is stale, tell the PR's agent to `git merge origin/<M>`
     (never rebase or force-push), re-run the gates and push.
   - If the bot has a re-trigger command, use it. Brooke's is `/prrb`, when
     there's no eyes reaction after about 60 s.
6. **When the review lands,** check the escalation triggers first, while
   the PR is still on Sonnet (see **Escalating to Opus**). For a Brooke
   review, run
   `${CLAUDE_SKILL_DIR}/../github-issue-burndown/scripts/brooke-security.sh O/R P`.
   Unless a trigger fires, message the same agent with SendMessage:
   "Run `github-address-pr-review <P>` in your worktree, keep the gates green,
   push, and report each comment's disposition and the new head SHA."
   Count the address rounds per PR in the state file.
7. **Before merging, check the conditions yourself:**
   - the PR's base is `<M>` (`gh pr view P --json baseRefName`), not `main`;
   - CI is green on the *new* head: `gh pr checks P`;
   - the review exists;
   - replies were posted;
   - `mergeStateStatus` is clean.

   If all hold, run `gh pr merge P --merge`, or use the strategy the repo's
   history uses.
8. **Close the sub-issue yourself.** `Closes #N` only fires on a merge into
   the default branch, so run
   `gh issue close N --reason completed --comment "Merged into <M> by #P; reaches main with the milestone merge."`
   The blocked-by edges count it as done from then on.
9. **Clean up.** First delete the worktree's build output. Then remove the
   worktree, delete the local branch and fetch. Re-check which issues are now
   unblocked.
   - If the repo has its own script for this, use it. okf_mcp has
     `tools/agentic/remove-worktree.sh <path> --branch` (issue #549).
   - Otherwise, in a Rust repo (a `Cargo.toml` at the worktree root), run
     `cargo clean` in the worktree before `git worktree remove`:
     ```bash
     (cd .worktrees/<repo>-<N> && timeout 10m cargo clean)
     git worktree remove .worktrees/<repo>-<N>
     ```
     `~/.cargo/config.toml` sets a `build-dir` outside the checkout, one
     hashed directory per worktree, and `git worktree remove` leaves it
     behind. On okf_mcp epic #507 each agent worktree left 30-47 GiB, and
     the disk filled twice in a day. `cargo clean` deletes that build
     directory as well as `target/`.
   - Don't clean while the agent or anything else is still running in
     that worktree.

### Escalating to Opus

Opus takes over a PR from its Sonnet implementer only on one of these
triggers:
- **Security:** the reviewer marks a security problem blocking and sinks
  the score. For Brooke, `brooke-security.sh` prints `ESCALATE`: a score
  under 80 with a `**Blocking:**` item in her `### Security` section.
- **Review rounds:** two Sonnet address rounds are done and the review on
  the new head still has blocking or inline comments.
- **CI:** the agent has failed twice to get CI or the gates green on its
  own changes, not on a known flake.

An agent reporting the sub-issue as ambiguous or as conflicting with the
plan isn't a trigger. Take that to the user.

To escalate:
1. Tell the Sonnet agent to stop every loop it started and report. Check
   that nothing still runs in the worktree.
2. Start a new `issue-implementer` with `model: "opus"` on the **same**
   worktree, branch and PR. Its brief is the normal one with **What to do**
   replaced by: the PR and head SHA it takes over, the trigger and its
   evidence, the rounds so far and the reviewer's unresolved points, then
   "run `github-address-pr-review <P>`, build on the existing work, don't
   start over". It answers every later round.
3. Record `model: opus (<trigger>: <evidence>)` in the state file and in
   your report, for example
   `opus (security: score 58, Blocking: cross-account cache disclosure)`.
   A model change without a recorded trigger is a mistake.

If Opus has done two address rounds and the review is still blocking, stop
on that PR. Report it to the user with the reviewer's points, and carry on
with the other sub-issues.

When `<M>` moves under an open PR because another PR merged, tell that PR's
agent to merge `origin/<M>` before its review, or right after it.

**When `main` moves** (a hotfix landed), bring it into `<M>` soon, so the
final merge stays small and the milestone is tested against production code.
Don't push a merge straight to `<M>`. Open a sync PR:
```bash
git worktree add .worktrees/<repo>-sync-<date> -b sync-main-into-<M>-<date> origin/<M>
git -C .worktrees/<repo>-sync-<date> merge origin/main   # never rebase
```
Push it and open a PR into `<M>`. If the merge was clean, merge the PR once CI
is green, without a review: its code was already reviewed on `main`. If you
had to resolve conflicts, request a review as for any PR. Then have the
agents of open PRs merge `origin/<M>`.

## Keeping your context small

Every turn re-reads your whole context. In the week to 2026-11-21,
coordinator sessions ran at a median of 430k context tokens, peaked near
900k, and took 400-900 turns per epic. The coordinator alone was 20-50% of
a run's tokens.

1. **State file.** Keep the run's state in
   `$(git rev-parse --git-common-dir)/coordinator/epic-<epic>.md`, outside the
   tree. Record the milestone branch, reviewer, gates, merge authorization and
   one line per sub-issue: status, worktree, branch, PR, agent id, model,
   review round and next action. Update it at every state change: agent
   started, PR opened, review landed, merged, cleaned up. A compacted or
   fresh session carries on from this file. Don't write expanded plugin paths
   (`~/.claude/plugins/cache/<market>/<plugin>/<version>/...`) into it, or into
   briefs and memory: a session keeps the plugin version it loaded, so after
   an update or a compact a copied path runs old scripts, or none. Write
   `${CLAUDE_SKILL_DIR}/...` and take the real path from the skill as loaded.
2. **Checkpoint, then suggest a compact.** Update the state file at each of
   these points:
   - when planning or brainstorming ends, before the first agent starts;
   - after every third merge into `<M>`;
   - before `github-epic-close-out`.

   End that message with a line ready to paste:
   `/compact Continue github-epic-to-merged-prs <epic> from <state file>. Keep agent ids, open PRs and their next actions.`
   You can't run `/compact` yourself, so don't wait for it; keep driving
   the loop. Background agents and watchers carry on through a compact, and
   SendMessage still reaches agents by id.
3. **Resume.** If a state file exists for the epic, or you're invoked with
   `--resume`, read it. Check it against GitHub (`gh pr list --base <M>` and
   the sub-issues' states) and the running agents, then carry on from there.
   Skip the pre-flight checks the file already records.
4. **Fewer, cheaper turns.**
   - Use one background watcher per PR that waits for the review, then for
     CI, and prints one line. Don't run separate watchers and spot checks.
   - Don't check on a running agent or watcher. You're notified when it
     finishes.
   - Read only the fields you need: `--jq` on API calls, `tail` on logs,
     review comments as `path:line body`.
   - Batch catalog updates into one changeset per checkpoint, not one per PR.
5. **Compaction.** The `github-workflows` plugin's `PreCompact` hook prints this state
   file into every compaction, manual or automatic, so the summary keeps it. For sessions
   that run coordinators, set `autoCompactWindow` to about 300000 (user settings, or
   `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000 claude` for one session) so auto-compact fires
   long before the 1M window and the run can carry on unattended. Much below 200000
   compacts too often to pay off, and the setting applies to every session where it is
   set. The checkpoints above still compact at clean points; the window is the ceiling.

## The agent brief

Each agent knows only its `issue-implementer` definition and its brief.
The definition covers the standing rules, so the brief holds what's specific
to this issue. Repeat a standing rule only to override it. Use these sections:

```
You are implementing GitHub issue #<N> (<title>) in <owner>/<repo>.

## Where to work
Work ONLY in <abs worktree path>, branch <branch>, created from origin/<M> at <sha>.
Base branch: <M> (the milestone integration branch). Open the PR with --base <M>, never main,
and use origin/<M> wherever a skill says origin/main or the default branch.
That base includes: <merged sibling issues>. Use absolute paths; don't cd to the main checkout.

## What to do
Run the `github-issue-to-pr` skill with argument `<N>` and follow it end to end.

## Project specifics
- The plan <path> is authoritative; this issue is Task <k>. If the code has to differ,
  correct the plan in the same PR with a dated "> **Corrected (issue #<N>).**" note.
- <changelog convention, known flakes and how to recognise them, decisions to honour>

## Parallel work
<other open PRs and the files they touch>

## Gates
<lint and test commands> must be green before you push.

## Shared machine
- Write logs only inside your worktree (e.g. target/i<N>-logs/).
- Never kill processes by pattern; kill only PIDs you started.
- Don't add CPU load.

## When done
Don't merge. <commit and PR attribution lines>. Report the PR URL, gate results with
test counts from YOUR log, and plan divergences. Keep your context: I'll message you
to run `github-address-pr-review` once <reviewer> has reviewed.
```

## Common mistakes

| Mistake | Fix |
|---|---|
| Polling for login `reviewer` when the API says `reviewer[bot]` | Match with `startswith`. Check the login on one real review first. |
| Treating "no review" as a lost webhook | Read the bot's issue comments: a stale branch is the usual cause. |
| Agents sharing a log directory and reporting each other's counts | Keep logs per worktree, and take counts from the agent's own log. |
| An agent's `pkill -f <binary>` killing other agents' test servers | Kill by PID only. Put this in every brief. |
| Waiting with `until ! pgrep -f "just lint"` | That matches every session's runs, so it can wait forever. Run your own job in the background and wait for its exit notification. |
| A hand-written review watcher with no deadline (okf_mcp PR #1008, 2026-11-24) | The bot ignored a re-request and the loop waited about 3 hours, because nothing else wakes a coordinator. Use the repo's watcher, then `wait-brooke.sh`, and only then your own loop, with a deadline (step 4). |
| Running a plugin script by a path copied into the state file (`.../github-workflows/0.1.0/...` after 0.1.3 was installed, okf_mcp epic #958) | The copy outlives the version the session follows: after an update it runs old scripts, and once old versions are pruned it fails mid-run. Store `${CLAUDE_SKILL_DIR}/...` and resolve it from the loaded skill. |
| Writing your own loop for what a repo script does (`gate.sh`, `watch-review.sh`, `merge-reviewed.sh`) | The scripts carry the timeouts, locks and re-triggers the loop lacks. If the repo has them, use them; write a loop only when it has none. |
| A CI watcher that waits for a fixed number of check runs | Older branches lack jobs added to `main` since, so it waits forever. Wait until runs appear, allow a grace period, then require none pending. |
| A review watcher that counts only stale notices posted after it started | It misses a notice already posted. Match a notice that names the PR's current head SHA, whenever it was posted. |
| A CI watcher that ignores merge conflicts | Each merge to `main` can conflict with the open PRs. Check `mergeable` first, and report `CONFLICTING` instead of waiting on CI. Check it again once CI finishes, waiting out `UNKNOWN` (GitHub recomputes it after `main` moves). After every merge, re-check the other open PRs. |
| Starting the implementer as `general-purpose` (or with no `subagent_type`) | It inherits the parent's model (Opus) and none of the standing rules. Always use `subagent_type: "github-workflows:issue-implementer"`. |
| A new agent addressing the review | Use the original agent, which has the context. The one exception is an escalation to Opus, which takes over for every later round. |
| Starting an implementer on Opus because the sub-issue touches locks, migrations or security | Always start on Sonnet. Opus only takes over on a recorded trigger (security block, two rounds, two CI failures). |
| Merging on the agent's word | Check CI, the review and the replies yourself. |
| Merging without explicit authorization | Stop at "ready to merge" and report. |
| Starting a blocked issue, or two issues that edit the same files | Respect the blocked-by edges. Serialize file overlaps. |
| A sub-issue PR opened against `main` | Check `baseRefName` before merging. Retarget with `gh pr edit P --base <M>`, then have the agent merge `origin/<M>`. |
| Waiting for a sub-issue to auto-close | `Closes #N` doesn't fire on a non-default base. Close it yourself after the merge. |
| Letting `main` drift from `<M>` for the whole milestone | Sync each hotfix into `<M>` through a sync PR, so the final merge holds no surprises. |
| `git worktree remove` without `cargo clean` first | The worktree's build directory under `~/.cache/cargo-build/` is left behind, 30-47 GiB per agent worktree. Clean first (step 9). To clean up after the fact, re-create the worktree at the same path, run `cargo clean` there, and remove it again. The build directory's hash depends only on the path. |
| Writing "closes #N" or "doesn't close #N" in the milestone PR body | Any closing keyword before an issue number closes it on merge, negated or not, so the epic closes before the final audit. Leave the keywords out: "The epic stays open until the post-merge audit." |
| Squash-merging the final PR | Use a merge commit: it keeps each PR's history and the claims ledger's commit anchors. |

## Finishing

After the last sub-issue merges into `<M>`:
1. Remove any worktrees that are left, sync and audit worktrees included,
   running `cargo clean` in each first (step 9). Sync `main` into `<M>` one last time
   (as above) if it has moved.
2. **REQUIRED: invoke `github-epic-close-out <epic> --branch <M>`.** In
   pre-merge mode it audits every sub-issue, PR, plan task and design
   checkpoint against `origin/<M>`, and reports whether the milestone is ready
   for `main`. Don't open the final PR unless it validates.
3. **Open the milestone PR** from `<M>` into `main`. Its body lists the
   sub-issues and their PRs and links the close-out audit comment. Wait for CI
   green on its head and `mergeStateStatus` `CLEAN`. Request a review only if
   the project's reviewer is wanted on milestone PRs, or the sync merges
   needed conflict resolution; the pieces were reviewed already.
   **Keep closing keywords out of the body.** `close`, `closes`, `closed`, `fix`, `fixes`,
   `fixed`, `resolve`, `resolves` and `resolved` followed by an issue number close that issue when the PR
   merges into `main`, and negation doesn't stop it: "doesn't close #3" still closes
   #3 (PR #25 closed epic #3 before the final audit ran). Write "The epic stays open
   until the post-merge audit" and refer to issues as "epic #3" or "sub-issue #12".
4. **The final merge.** Ask the user for the go-ahead (unless the standing
   authorization explicitly covers it), then run `gh pr merge <P> --merge`.
   Never squash or rebase this one.
5. **Re-run `github-epic-close-out <epic>`** against `main`: it confirms the
   merge commit is on `main` and CI on `main` is green, then closes the epic.
   Don't close the epic yourself. Then delete `<M>`
   (`git push origin --delete <M>`) once the epic is closed.
6. Record what you learned in the catalog: flakes, root causes, decisions, the
   reviewer's quirks. Put anything left unfixed in `/projects/things-to-fix.md`.

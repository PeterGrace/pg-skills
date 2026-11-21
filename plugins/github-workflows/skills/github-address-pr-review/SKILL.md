---
name: github-address-pr-review
description: "Autonomous per-comment sibling to `github-pr-address-comments`. Walks the review comments on an open GitHub pull request one comment at a time using the `gh` CLI. For each comment, Claude reads the feedback against the code and decides on its own between three dispositions — apply (edit, commit, reply), explain (reply with a justification, no code change), or ignore (no change, no reply) — and carries that decision out fully without asking the user anything. Use this skill whenever the user asks Claude to \"walk through the review comments on PR N\", \"go through the feedback on <github-pr-url> one by one\", \"address the review on PR N comment by comment\", \"work through each comment on PR N\", or any similar phrasing that implies handling review feedback per comment. This is a fully autonomous workflow — never stop to ask the user how to dispose of a comment or to confirm any follow-on step (edit, commit, push, reply)."
---

# GitHub — Address PR Review, Comment by Comment

Autonomous workflow: read the comments on an open pull request, check out its head branch, then walk each comment one at a time. For every comment, weigh the reviewer's ask against the actual code and **decide yourself** how to dispose of it — apply a change, explain why no change is needed, or ignore it — then carry that decision out end to end (edit, commit, push, reply).

**Never ask the user to answer anything during this skill.** Not for a disposition, not for a confirmation, not for a skip reason, not for an edge case. Wherever a judgment call comes up, make the best call you can, act on it, and record the reasoning in the final report. If something genuinely blocks progress (no auth, not a git repo, can't determine the repo), stop and report — don't ask.

This skill is a sibling to `github-pr-address-comments`. Same source material, same prerequisites, same commit-message shape. The difference is granularity: this skill reasons about and acts on each comment individually, narrating its decision per comment as it goes, rather than classifying the whole batch up front.

## Prerequisites

Before starting, check:

1. **Inside a git repository.** `git rev-parse --show-toplevel` should succeed. If not, stop and report.
2. **The `gh` CLI is installed and authenticated.** Run `gh auth status`. If `gh` is missing or unauthenticated, stop and report — suggest the user run `! gh auth login` themselves, since it is interactive.
3. **Working tree is clean.** Run `git status --porcelain`. If there are uncommitted changes, stash them automatically so nothing is lost when switching branches:

   ```bash
   git stash push --include-untracked -m "github-address-pr-review: auto-stash before PR <number>"
   ```

   Record the stash ref and the branch you were on. At the end of the run, switch back to that original branch and leave the stash in place (do not pop it onto the PR branch). Mention the stash and how to restore it (`git checkout <original-branch> && git stash pop`) in the final report.
4. **Remote is up to date.** Run `git fetch origin` so the local view of the PR branch matches what GitHub has. Skipping this leads to operating on a stale branch.

## Step 1: Identify the target PR

Extract two things from the user's request: the **PR number** and the **repo** (`owner/name`). The user will usually only give the PR number and expect you to infer the repo from the current directory.

`gh` infers the repo from the git remote automatically, so inside the repo you can usually just use the PR number. To confirm what it resolved to:

```bash
gh repo view --json nameWithOwner,defaultBranchRef -q '.nameWithOwner, .defaultBranchRef.name'
```

If the user gave a full PR URL like `https://github.com/myorg/myrepo/pull/42`, parse owner/repo/number from the URL — the URL wins over the current remote. Pass it explicitly with `--repo myorg/myrepo` on every `gh` call. (Note GitHub's PR URL path is `/pull/N`, singular — unlike Forgejo's `/pulls/N`.)

If neither gives you owner/repo, stop and report that the repo could not be determined.

Note: for a GitHub Enterprise host, the URL host will not be `github.com`; `gh` handles this if the host is configured (`gh auth status` shows it). If it isn't, stop and report.

## Step 2: Fetch the PR and its comments

Retrieve the PR itself:

```bash
gh pr view <number> --json number,title,body,state,headRefName,baseRefName,url,reviews,comments
```

Also pull comments from BOTH sources — and on GitHub these are genuinely different API objects, so be precise about which is which:

- **Issue comments** (a.k.a. timeline / conversation comments) — top-level comments on the PR thread. These are the `comments` field above, or `gh api repos/{owner}/{repo}/issues/<number>/comments`, or `gh pr view <number> --comments` for a readable rendering. GitHub stores PR conversation comments on the *issues* endpoint, which is why the path says `issues`.
- **Review comments** (inline, line-anchored) — code-anchored comments left during a review:

  ```bash
  gh api repos/{owner}/{repo}/pulls/<number>/comments --paginate
  ```

  Each returns `id`, `path`, `line`, `body`, `user.login`, `in_reply_to_id`, and `diff_hunk`. The `id` here is the numeric REST id — that is what the reply endpoint in Step 5 wants.

There is also a third thing GitHub exposes that Forgejo folds in elsewhere: the **review body** — the summary text a reviewer writes when submitting an APPROVED / CHANGES_REQUESTED / COMMENTED review. Those are in the `reviews` field of the `gh pr view` call above, or `gh api repos/{owner}/{repo}/pulls/<number>/reviews`. A non-empty review body is real feedback and belongs in the walk; an empty one is just the verdict and should be dropped.

You need all of these. Some reviewers use conversation comments for general feedback and inline comments for specific code asks; others put everything in the review body. Walking only one source leaves comments unanswered.

Comments arriving from `in_reply_to_id` are replies inside an existing thread. Group them under their parent so each thread is considered once, not N times, and reply to the parent's `id`. Read the whole thread before deciding — a later reply may have already settled or withdrawn the ask.

From the PR response, record:

- **state** — if it's `CLOSED` or `MERGED`, do not make any commits or post any replies: the branch is dead and replies would land on a finished thread. Skip straight to the final report, listing every comment as **not walked (PR closed/merged)**.
- **head** — the source branch (`headRefName`) and the head repo. `gh pr view <number> --json headRepositoryOwner,headRepository,isCrossRepository` tells you whether **this PR is from a fork** (`isCrossRepository: true`); handle per Step 3.
- **base** — the target branch (`baseRefName`).
- **mergeable / conflict state** — `gh pr view <number> --json mergeable,mergeStateStatus`. Surface in the final report; do not try to resolve conflicts as part of this skill.
- **author** — useful context.

From each comment, keep **id**, **author**, **body**, **created_at**, **path** and **line** if inline, and any resolved-state flag the server exposes.

**Resolved threads**: GitHub's REST API does *not* expose whether a review thread is resolved — that lives only in GraphQL, under `pullRequest.reviewThreads { isResolved, isOutdated }`. Always run this query so already-resolved threads can be ignored rather than re-litigated:

```bash
gh api graphql -f query='
  query($owner:String!, $repo:String!, $number:Int!) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$number) {
        reviewThreads(first:100) {
          nodes { isResolved isOutdated comments(first:1) { nodes { databaseId path } } }
        }
      }
    }
  }' -F owner=<owner> -F repo=<repo> -F number=<number>
```

Match threads back to REST comments via `databaseId`. If the query fails, continue without it and say so in the final report rather than implying nothing was resolved. Note also that *resolving* a thread is likewise GraphQL-only (`resolveReviewThread` mutation) and not something `gh` exposes directly — this skill posts replies, it does not resolve threads.

If any of these endpoints errors or comes back empty in a way that looks wrong, verify with `gh api` first before assuming the data isn't there, and note in the final report that inline review comments were not surfaced if you end up walking conversation comments only.

## Step 3: Check out the PR's head branch

Same-repo PR (the common case):

```bash
git fetch origin <head-ref>
git checkout <head-ref>
git pull --ff-only origin <head-ref>
```

`--ff-only` is deliberate: if the local branch has diverged from the remote, fail loudly rather than silently merging or rebasing. A diverged branch usually means there's local work that must not be overwritten. If the fast-forward fails, do not force anything: continue the walk in **reply-only mode** (apply is unavailable, as for a fork PR below) and note the divergence in the final report.

`gh pr checkout <number>` will also do this and handles the fork case by adding the right remote — but it can rebase or force-update the local branch, so prefer the explicit sequence above when a local branch already exists.

**Fork PR**: the PR's head lives on a fork you probably cannot push to. Do **not** attempt the checkout. Run the walk in **reply-only mode**: only **explain** and **ignore** are available. For a comment you would otherwise have applied, post an explain-style reply describing the concrete change you recommend (with a small code snippet if helpful) so the PR author can apply it, and record it in the report as **recommended (fork — not applied)**.

## Step 4: Pre-walk filter

Drop bot/CI noise comments from the walk so effort isn't spent on automated chatter. Heuristics for filtering:

- `user.type` is `Bot` — GitHub tags App-authored comments this way, and it is more reliable than name matching. Author login ends in `[bot]`.
- Author name ends in `-bot`, `-actions`, or `-ci`.
- Author matches a known automation name (`github-actions`, `dependabot`, `renovate`, `codecov`, etc.).
- Body starts with a recognizable CI status preamble (e.g. `## Build status`, `> [bot] ✅ Tests passed`).

Careful with **bot reviewers** that leave substantive inline review comments (Copilot code review, `sonarcloud`, various linters posting via review API). Those are `user.type: Bot` but are real, actionable feedback. Filter automated *status* chatter, not automated *code review*: if a bot comment is line-anchored with a concrete code ask, keep it in the walk.

When in doubt, **include** the comment — it costs little to evaluate it and choose **ignore** in the loop. Silently dropping a real piece of feedback because a heuristic misfired is worse than evaluating one noisy comment.

After filtering, announce the working count (informational — do not wait for a response):

> Found 7 comments to work through. Starting with #1 of 7.

If the count is zero, report it and stop — there is nothing to address. Do not invent work.

## Step 5: Autonomous per-comment loop

For each comment (or thread) in source order, oldest first: read it, inspect the code it refers to, decide on a disposition, carry it out, and move on. Do not pause between comments.

### Per-comment narration

As you handle each comment, print a short status block so the user can follow along (this is output, not a question):

- `#N of M` — reviewer handle.
- A ≤2-line quoted excerpt of the comment body (truncate with `…`).
- File path and line number if inline; `[stale anchor]` if the anchor is outdated.
- **Decision:** `apply` / `explain` / `ignore`, with a one-sentence reason.
- The outcome (commit SHA and reply queued, reply posted, or "no action").

### Deciding the disposition

Read the full comment, its thread, and the surrounding code (for inline comments, ~10+ lines around the line, or the `diff_hunk` if the anchor is stale). Then pick exactly one:

| Disposition | When to choose it |
|-------------|-------------------|
| **apply**   | The reviewer identified a real bug, a clear improvement, a style/convention violation, a missing test or doc, or anything where the change is reasonable, low-risk, and within the PR's scope. Default toward apply when the ask is sensible and cheap — reviewers' time matters and small asks should just be done. |
| **explain** | The reviewer asked for a change (or asked a question) that deserves a response, but the current code is correct or the change would be wrong — e.g. it would break an invariant, contradict the spec or PR description, conflict with an established project pattern, duplicate handling that exists elsewhere, or expand scope well beyond the PR. Also use for direct questions that can be answered without a code change. |
| **ignore**  | The comment needs neither a code change nor a reply: praise or acknowledgments ("LGTM", "nice", "thanks"), bot chatter that slipped past the filter, threads already resolved (per the GraphQL query), asks already addressed by a later commit or already withdrawn later in the thread, comments superseded by a later comment, or comments the PR author left as notes to themselves. |

Guidelines for judging:

- Prefer **apply** over **explain** when you are on the fence and the change is small and safe. Prefer **explain** over **apply** when the change is large, risky, ambiguous, or would alter behavior the PR description explicitly calls for.
- If the ask is ambiguous (two reasonable readings), choose the reading that best fits the code and the PR's intent, apply it, and say in the reply which interpretation you took.
- If a "nit" or optional suggestion is reasonable, apply it; if it's purely a matter of taste and the existing code follows project convention, explain.
- Never choose **ignore** for a substantive ask just to avoid work. Ignore is for comments where a reply would be noise.
- Don't capitulate when the current code is demonstrably correct, and don't argue for the sake of arguing.

### apply — edit, commit, queue the reply

1. Make the minimal code edit that satisfies the ask. Do not drive-by refactor.
2. Show the unified diff in the output (informational).
3. If the edit produced no change (the file is already in the desired state), do not create an empty commit — reply that it's already addressed and record **already addressed** in the report.
4. Stage and commit:

   ```bash
   git add <changed-files>
   git commit -m "$(cat <<'EOF'
   <type>: <imperative summary>

   Addresses review comment from @<reviewer>:
   > <first sentence or two of the original comment>
   EOF
   )"
   ```

   `<type>` follows conventional-commit-style buckets (`fix`, `refactor`, `docs`, `chore`).

5. **Draft** a reply pointing at the commit, and **queue it; don't post it yet**:

   > Addressed in `<short-sha>` — <one sentence on what changed and why it meets the ask>.

   The commit exists only locally until Step 6 pushes it. GitHub links a SHA in a comment only if it already knows the commit when the comment is posted, so a reply posted now shows the SHA as plain text and never gets linked. Write the body to a file now, record which comment it answers, and post it in Step 6b. If a later fix in this session amends or adds to the commit (validation fixes, `chore: fmt`), update the queued reply's SHA, or name both commits.

   How to post it (in Step 6b):

   For **inline review comments**, reply in-thread against the comment's REST `id`:

   ```bash
   gh api repos/{owner}/{repo}/pulls/<number>/comments/<comment_id>/replies \
     -F body=@<path-to-reply.md>
   ```

   For **conversation comments** and **review bodies**, there is no threaded reply — post a top-level comment instead:

   ```bash
   gh pr comment <number> --body-file <path-to-reply.md>
   ```

   Write reply bodies to a file in the scratchpad and use `--body-file` / `-F body=@file` rather than fighting shell quoting on multi-line text.

### explain — reply, no code change

1. Draft a short justification citing a specific reason — an invariant, a prior decision, a constraint from the spec or PR description, or a pointer to where the concern is already handled. Template:

   > Leaving as-is: <one or two sentences>. Happy to change it if you disagree.

   For a plain question, just answer it concisely.

2. Post it now, via the same inline-vs-conversation split as apply, then advance. An explain reply names no commit, so it doesn't wait for the push. If it does mention a commit, queue it like an apply reply.

A good explain reply is short, specific, and invites the reviewer to push back.

### ignore — no change, no reply

Record the comment and a one-line reason (e.g. "praise, no action", "thread already resolved", "superseded by @x's later comment", "bot status message") for the final report, then advance. Post nothing.

## Step 6: Batched validation and push (only if ≥ 1 commit was made)

If the walk produced zero commits, skip this step entirely — there is nothing to validate or push.

Otherwise, run from the repo root, in order:

```bash
just fmt
cargo clippy --all-targets -- -D warnings
just test
```

**Graceful degradation:**
- No `Cargo.toml`: skip `cargo clippy` and note in the final report.
- No `justfile`, or missing `fmt` / `test` recipes: skip the missing tools and note in the final report. Do not silently substitute different commands.
- `-D warnings` on clippy treats warnings as errors. If clippy fails only on warnings that pre-date this session's commits, re-run without `-- -D warnings` and surface the warnings in the final report.

**On success:** push the branch.

```bash
git push origin <head-ref>
```

If `fmt` reformatted files, commit those changes as a follow-up `chore: fmt` commit before pushing so they reach the remote.

**On validation failure:** first try to fix it yourself if the failure is clearly caused by one of this session's commits (e.g. a compile error, a failing test you can trace to your edit) — make the fix, commit it, and re-run validation. Make at most two such fix attempts. If it still fails, stop. **Do not push** — never push code that fails validation. **Do not auto-revert commits.** Print which check failed with the relevant output, and include in the report:

> `N` commits made on `<head-ref>` (not pushed — validation failed on `<check>`). Fix and re-validate manually, then push, or run `git reset --soft HEAD~N` to unwind these commits.

Do not post the queued apply replies: they would name commits GitHub doesn't have. List them in the report as **drafted, not posted**, with their file paths, so they can be posted after a manual push.

**Push failure** (rejected, auth, etc.): surface the error and the exact `git push origin <head-ref>` command so the user can retry. The commits are safe locally. As with a validation failure, leave the queued replies unposted and list them.

## Step 6b: Post the queued replies (after a successful push)

Post the apply replies only once GitHub has the commits:

1. Check that the pushed head matches the local head: `git ls-remote origin <head-ref>` should print `git rev-parse HEAD`.
2. Check that GitHub's API resolves every SHA the queued replies name:

   ```bash
   gh api repos/{owner}/{repo}/commits/<sha> -q .sha
   ```

   If any lookup fails, give GitHub a few seconds and check again (up to about a minute) before posting. Don't post a reply whose commit doesn't resolve yet.
3. Post the queued replies in walk order, using the inline-vs-conversation split from Step 5. Record any post that fails and keep going.

If the walk made no commits, the queue is empty and this step does nothing.

Finally, if a stash was created in Prerequisites, check out the original branch again (leave the stash in place).

## Step 7: Final report

End every invocation with this report, even on failure:

- PR number and URL.
- Counts per disposition: **applied** (with commit SHAs), **explained**, **ignored** (with a one-line reason each), **recommended (fork — not applied)**, **already addressed**, **not walked** (with why, e.g. PR closed).
- A compact per-comment table: reviewer, excerpt, decision, reason.
- Commit SHAs created in this session.
- Validation status, per tool: `just fmt` ✅/❌/skipped, `cargo clippy` ✅/❌/skipped, `just test` ✅/❌/skipped.
- **Push status**: pushed ✅ to `<head-ref>`, or **not pushed** with the reason (validation failed / push rejected / no commits made / reply-only mode) and the `git push origin <head-ref>` command to retry.
- Any reply-post failures, with which comment they belonged to, and any apply replies **drafted, not posted** because the push didn't happen (with their file paths).
- Any auto-stash created, and how to restore it.

Keep it tight. The PR URL, the per-comment decisions, the commit list, and the push status are the point.

## Edge cases worth remembering

- **Dirty working tree at the start**: auto-stash with `--include-untracked`, return to the original branch at the end, leave the stash in place, report it. Never discard the user's work.
- **PR is from a fork**: reply-only mode. Apply-worthy comments get a reply describing the recommended change. Announce at the start of the walk.
- **Local branch diverged from remote**: don't force or rebase; reply-only mode, noted in the report.
- **PR is closed or merged**: no commits, no replies; report every comment as not walked.
- **No comments after Step 4 filter**: report and stop. Do not invent work.
- **User's own comment on the PR**: evaluate it normally. A to-do-style note from the PR author ("TODO: rename this") is usually an apply; a note to self with no ask is an ignore.
- **Bot/automation comment that snuck past the filter**: ignore it. Don't fail the session over filter misses.
- **Bot *reviewer* with substantive inline comments** (Copilot review, linter bots): evaluate on the merits like any human comment — bots are wrong more often, so apply only if the ask holds up against the code.
- **Outdated / stale review comment** (`line` is null, `position` is null): use `original_line` / `original_start_line` and `diff_hunk` to reconstruct what the reviewer was looking at, then locate the code by content. If the concern no longer applies to the current code, ignore (or explain briefly if the reviewer asked a direct question). Replies still post normally.
- **Comment references code you cannot unambiguously locate** (file renamed, function moved, etc.): search the repo by content. If you still can't locate it, choose explain and reply asking the reviewer to point at the current location — that's a question to the reviewer on GitHub, not to the user.
- **Already-resolved thread** (per GraphQL): ignore. Resolving threads is not something this skill does.
- **Reply endpoint 404s**: the `/pulls/N/comments/{id}/replies` endpoint only accepts a **top-level** review comment id. Replying to a comment that is itself a reply (`in_reply_to_id` is set) needs the parent's id. If unsure an endpoint or field exists, verify with `gh api` first rather than guessing.
- **Inline reply fails or the comment isn't a review comment**: fall back to `gh pr comment <number> --body-file <file>` with a quoted excerpt of the original comment so the thread linkage is at least visible. Note this in the final report.
- **Reply post fails mid-loop**: record the failure with which comment it belonged to, continue the loop. List failures in the final report so the user can re-post manually.
- **Two reviewers contradict each other on the same code**: you are the arbiter. Pick the position best supported by the code, the PR description, and project conventions; apply it if it requires a change, reply to the comment you followed with the commit, and reply to the other explaining the trade-off and why you went the other way.
- **Several comments ask for the same change**: apply it once; reply to each pointing at the same commit.
- **Project has no `justfile` or no `Cargo.toml`**: Step 6 degrades per its own rules. Do not silently substitute commands.
- **Rate limiting on a very chatty PR**: `--paginate` on the comments endpoint can be several requests. `gh api rate_limit` shows remaining budget if calls start failing.

## Coexistence with `github-pr-address-comments`

Both skills are autonomous. A bare phrase like *"address the review on PR 42"* could plausibly match either; description-line wording is what disambiguates them to the router.

- **Sibling (`github-pr-address-comments`)** triggers on batch phrasing: *"address"*, *"handle"*, *"go through and push fixes"*, *"respond to"*. Classifies the whole batch up front and acts on it.
- **This skill (`github-address-pr-review`)** triggers on per-comment phrasing: *"walk through"*, *"one by one"*, *"comment by comment"*, *"work through each comment"*. Reasons about and narrates each comment individually, choosing apply / explain / ignore per comment.

The two skills share the same commit-message shape and validation discipline, so a PR can be handled by either skill in different rounds without inconsistency.

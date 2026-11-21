---
name: forgejo-address-pr-review
description: "Walks a user through the review comments on an open Forgejo pull request one comment at a time using the `raohwork/forgejo-mcp` server. For each comment, presents a suggested resolution and prompts the user with five options (accept / explain / skip / expand / quit). The per-comment choice is the only approval gate: once the user picks a disposition, Claude carries it out fully — editing files, committing, pushing, and posting replies — without asking for further confirmation. Use this skill whenever the user asks Claude to \"walk me through the review comments on PR N\", \"let's go through the feedback on <forgejo-pr-url> one by one\", \"address the review on PR N interactively\", \"suggest fixes for each comment on PR N\", or any similar phrasing that implies wanting per-comment suggestions and human-in-the-loop control rather than autonomous batch fixes."
---

# Forgejo — Interactively Address PR Review

Interactive, human-in-the-loop workflow: read the comments on an open pull request, check out its head branch, then walk each comment one at a time. For every comment, present the reviewer's quote alongside a suggested resolution and ask the user how to dispose of it. The user's per-comment choice is the approval — once they pick a disposition, carry it out end to end (edit, commit, push, reply) without further prompts.

This skill is the interactive sibling to `forgejo-pr-address-comments`. Same source material, same prerequisites, same commit-message shape — the difference is granularity of control. The sibling classifies and acts on every comment in one batch; this skill defers the *disposition decision* for each comment to the user. Once a disposition is chosen, both skills act without pausing. Reach for this when the right disposition isn't obvious from the comments alone and you want Claude's suggestions while still steering each comment.

## Prerequisites

Before starting, confirm:

1. **Inside a git repository.** `git rev-parse --show-toplevel` should succeed. If not, stop and tell the user.
2. **The `forgejo` MCP is connected.** Its tools show up with a `forgejo` prefix (likely `get_pull_request`, `list_issue_comments`, `list_pull_request_review_comments`, `reply_to_review_comment`, `create_issue_comment`). If they are not available, stop and tell the user the MCP is not connected.
3. **Working tree is clean.** Run `git status --porcelain`. If there are uncommitted changes, ask the user whether to stash them before continuing — this skill will switch branches and must not lose their in-flight work.
4. **Remote is up to date.** Run `git fetch origin` so the local view of the PR branch matches what Forgejo has. Skipping this leads to operating on a stale branch.

## Step 1: Identify the target PR

Extract two things from the user's request: the **PR number** and the **repo** (`owner/name`). The user will usually only give the PR number and expect you to infer the repo from the current directory.

Infer the repo from the git remote:

```bash
git remote get-url origin
```

Parse it:
- SSH form: `git@git.example.com:myorg/myrepo.git` → host=`git.example.com`, owner=`myorg`, repo=`myrepo`
- HTTPS form: `https://git.example.com/myorg/myrepo.git` → same
- Strip the trailing `.git` if present.

If the user gave a full PR URL like `https://git.example.com/myorg/myrepo/pulls/42`, parse owner/repo/index from the URL — the URL wins over the current remote.

If neither gives you owner/repo, stop and ask.

## Step 2: Fetch the PR and its comments

Call the `forgejo` MCP's `get_pull_request(owner, repo, index)` to retrieve the PR. Also pull comments from BOTH sources:

- **Timeline comments** via `list_issue_comments` — top-level comments on the PR thread (Forgejo stores PR timeline comments on the same endpoint as issue comments).
- **Inline review comments** via `list_pull_request_review_comments` — code-anchored comments left during a review.

You need both. Some reviewers use timeline comments for general feedback and inline comments for specific code asks; others use only one. Walking only one source leaves comments unanswered.

From the PR response, record:

- **state** — if it's `closed` or `merged`, warn and ask whether to proceed. You can still walk comments and post replies on a merged PR, but commits will land on a branch the upstream has already moved past.
- **head** — the source branch (`head.ref`) and the head repo (`head.repo.full_name` or equivalent). If `head.repo` differs from the base repo, **this PR is from a fork**; handle per Step 3.
- **base** — the target branch (`base.ref`).
- **mergeable / conflict state** — surface in the final report; do not try to resolve conflicts as part of this skill.
- **author** — useful context.

From each comment, keep **id**, **author**, **body**, **created_at**, **path** and **line** if inline, and any resolved-state flag the server exposes.

If `list_pull_request_review_comments` is not available on the connected MCP, note in the final report that inline review comments were not surfaced and walk timeline comments only.

## Step 3: Check out the PR's head branch

Same-repo PR (the common case):

```bash
git fetch origin <head-ref>
git checkout <head-ref>
git pull --ff-only origin <head-ref>
```

`--ff-only` is deliberate: if the local branch has diverged from the remote, fail loudly rather than silently merging or rebasing. A diverged branch usually means there's work the user doesn't want overwritten.

**Fork PR**: the PR's head lives on a fork you probably cannot push to. Do **not** attempt the checkout. Tell the user up front that the session is reduced: only `e` (explain) and `s` (skip) will be available in the per-comment loop. `a` (accept) is disabled for the whole session because there's no branch you can commit to.

If the user wants full `a` support on a fork PR, they need to (a) get push access to the fork — usually by being added as a collaborator or by the PR author enabling "allow edits from maintainers" — and (b) add the fork as a local remote. Then re-invoke the skill.

## Step 4: Pre-walk filter

Drop bot/CI noise comments from the walk so the user is not asked to dispose of automated chatter. Heuristics for filtering:

- Author name ends in `-bot`, `-actions`, or `-ci`.
- Author matches a known automation name (`gitea-actions`, `forgejo-actions`, `dependabot`, `renovate`, etc.).
- Body starts with a recognizable CI status preamble (e.g. `## Build status`, `> [bot] ✅ Tests passed`).

**Never filter `brooke-reviews[bot]`.** It is the user's own PR review tool, and reading its output is usually the whole reason this skill was invoked. Walk every comment it leaves, without exception.

Beyond that named case, be careful with **bot reviewers** in general (Copilot code review, `coderabbitai`, `sonarcloud`, linters posting through a review API). They are automated, but they produce real review output. Filter automated *status* chatter, not automated *code review*.

Crucially, keep a bot reviewer's comment even when it asks for **no change**. A verdict of "this is correct, no change needed" or "fine as-is, just a latent tripwire" is a reviewer's disposition, not noise -- the user may want to answer it, or may disagree with it. "Contains a concrete code ask" is the wrong keeper test; "reads as a human reviewer's comment would" is the right one.

When in doubt, **include** the comment — the user can dispose of it with one keystroke (`s`) in the loop. Silently dropping a real piece of feedback because a heuristic misfired is worse than asking about one noisy comment.

After filtering, announce the working count to the user:

> Found 7 comments to walk through. Starting with #1 of 7.

If the count is zero, report it and stop — there is nothing to address. Do not invent work.

## Step 5: Interactive loop

For each comment in source order (oldest first), present a terse view and prompt the user with five options. Walk the comments in order — the user can `s`kip a comment they realize has been superseded by a later one.

### Terse view (default)

For each comment, render:

- Reviewer handle.
- A ≤2-line quoted excerpt of the comment body. Truncate with `…` if longer; the user can `x`pand for the full text.
- File path and line number if the comment is inline.
- A one-paragraph proposed resolution — your reading of what the reviewer wants and how the current code should change (or why it shouldn't).

### Prompt

After the terse view, prompt:

> `[a]ccept` apply / `[e]xplain` reply / `[s]kip` / `[x]pand` for more context / `[q]uit` walk

The five inputs and their effects:

| Input | Action |
|-------|--------|
| `a`   | Accept: edit code → show diff → commit → queue the reply (posted after the push, Step 6b). No further confirmation — the `a` keystroke approves the whole sequence. |
| `e`   | Explain: draft justification → post reply. No code change, no further confirmation. |
| `s`   | Skip: record disposition and advance. |
| `x`   | Expand: re-render with full comment body and surrounding code context. Re-prompt. |
| `q`   | Quit: stop the loop, run Step 6 against any commits made, push if validation passes, print the report. |

### `a` — accept and apply

The `a` keystroke approves this entire sequence. Do not pause for confirmation between steps — the user already committed to applying the fix when they chose `a`. Show the diff for transparency, but keep moving.

1. Make the minimal code edit the suggestion describes. Do not drive-by refactor.
2. Show the user the unified diff of the change (informational — do not wait for approval).
3. Stage and commit:

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

4. Draft a reply pointing at the commit, without confirmation, and **queue it; don't post it yet**:

   > Addressed in `<short-sha>` — <one sentence on what changed and why it meets the ask>.

   The commit exists only locally until Step 6 pushes it. Forgejo links a SHA in a comment only if it already has the commit, so a reply posted now leaves the SHA unlinked. Keep the body and the comment it answers, and post it in Step 6b. If a later commit in this session changes the fix (validation fixes, a fmt commit), update the queued SHA, or name both commits.

   When posting in Step 6b, prefer `reply_to_review_comment` for inline review comments (lands in-thread); fall back to `create_issue_comment` for timeline comments or when the inline reply tool is unavailable.

If the user wants to back out a change after seeing the diff, they can say so in chat — but the default is to proceed. The commit, and the reply after the push, happen automatically once `a` is chosen.

### `e` — explain and reply

The `e` keystroke approves posting a justification reply. Draft it and post it — no confirmation step.

1. Draft a short justification citing a specific reason — an invariant, a prior decision, a constraint from the spec or PR description. Template:

   > Leaving as-is: <one or two sentences>. Happy to change it if you disagree.

2. Post it now, via the same inline-vs-timeline tool split as the accept sub-flow, then advance. It names no commit, so it doesn't wait for the push. If it does mention a commit, queue it like an accept reply.

A good `explain` reply is short, cites a specific reason, and invites the reviewer to push back. Do not capitulate when the current code is demonstrably correct, but do not argue for the sake of arguing either. If the user wants to revise the wording, they can say so in chat — but the default is to post and move on.

### `s` — skip

1. Ask the user (optional, one line) for a reason to record in the final report. Default: `user skipped`.
2. Advance to the next comment. No reply posted, no code changed.

### `x` — expand

1. Re-render the comment with:
   - The full body (no truncation).
   - For inline comments: ~10 lines of surrounding code from the file at the comment's line.
   - The skill's classification reasoning — why the suggested resolution is what it is.
2. Re-prompt with the same five options. `x` is informational only and does not advance the loop.

### `q` — quit walk

1. Stop the loop immediately.
2. Run Step 6 validation against any commits made so far, then push if it passes.
3. Post the queued accept replies (Step 6b) if the push succeeded.
4. Print the final report.
5. Remaining comments are recorded as **not walked** (distinct from skipped) in the report.

## Step 6: Batched validation and push (only if ≥ 1 commit was made)

If the walk produced zero commits (all comments dispositioned as `e`, `s`, or unwalked), skip this step entirely — there is nothing to validate or push.

Otherwise, run from the repo root, in order:

```bash
just fmt
cargo clippy --all-targets -- -D warnings
just test
```

**Graceful degradation:**
- No `Cargo.toml`: skip `cargo clippy` and note in the final report.
- No `justfile`, or missing `fmt` / `test` recipes: skip the missing tools and note in the final report. Do not silently substitute different commands.
- `-D warnings` on clippy treats warnings as errors. If too strict for this project, drop the `-- -D warnings` suffix and surface any warnings in the final report.

**On success:** push the branch automatically — no confirmation needed.

```bash
git push origin <head-ref>
```

If `fmt` reformatted files, those changes need to be committed before the push or they will not reach the remote; amend or add a follow-up commit as appropriate, then push.

**On validation failure:** stop. **Do not push** — never push code that fails validation. Print which check failed and the relevant output. **Do not auto-revert commits** — they may be partially salvageable, and reverting is the user's decision. Tell the user:

> `N` commits made on `<head-ref>` (not pushed — validation failed on `<check>`). Fix and re-validate manually, then push, or run `git reset --soft HEAD~N` to unwind these commits.

In that case, don't post the queued accept replies: they name commits Forgejo doesn't have. List them in the report as **drafted, not posted**.

**Push failure** (rejected, auth, etc.): surface the error and the exact `git push origin <head-ref>` command so the user can retry. The commits are safe locally. Leave the queued replies unposted and list them.

## Step 6b: Post the queued replies (after a successful push)

Post the accept replies only once Forgejo has the commits:

1. Check the push landed: `git ls-remote origin <head-ref>` must print the same SHA as `git rev-parse HEAD`.
2. Give Forgejo a few seconds to index the push before posting. If the PR's commit list, or the forgejo MCP's view of the PR head, still shows the old head, wait and check again (up to about a minute).
3. Post the queued replies in walk order, using `reply_to_review_comment` for inline comments and `create_issue_comment` otherwise. Record any post that fails and keep going.

If no commits were made, the queue is empty and this step does nothing.

## Step 7: Final report

End every invocation with this report, even on quit or failure:

- PR number and URL.
- Counts per disposition: **applied** (with commit SHAs), **explained**, **skipped** (with the user's reasons if given), **not walked**.
- Commit SHAs created in this session.
- Validation status, per tool: `just fmt` ✅/❌/skipped, `cargo clippy` ✅/❌/skipped, `just test` ✅/❌/skipped.
- **Push status**: pushed ✅ to `<head-ref>`, or **not pushed** with the reason (validation failed / push rejected / no commits made) and the `git push origin <head-ref>` command to retry.
- Any reply-post failures, with which comment they belonged to, and any accept replies **drafted, not posted** because the push didn't happen.

Keep it tight. The PR URL, the commit list, and the push status are the point.

## Edge cases worth remembering

- **Dirty working tree at the start**: ask before stashing; never silently move the user's work. This skill switches branches, which would blow up on a dirty tree anyway.
- **PR is from a fork**: do not attempt to push into a remote you don't control. `a` is disabled session-wide; offer `e` and `s` only. Announce at session start, not surprise mid-walk.
- **PR is closed or merged**: warn at Step 2. On merged PRs, replies still post but the thread is effectively dead — ask the user whether to suppress replies entirely for this session.
- **No comments after Step 4 filter**: report and stop. Do not invent work.
- **User's own comment on the PR**: walk it normally. No author-based filtering — the user might be reviewing their own PR for a teammate's benefit.
- **Bot/automation comment that snuck past the filter**: the user disposes with `s` in one keystroke. Don't fail the session over filter misses.
- **Comment references code the suggestion cannot unambiguously locate** (file renamed, function moved, etc.): mark the suggested resolution as `[needs human reading]` and default the prompt focus to `x` so the user gets context before deciding.
- **Inline reply tool missing from the MCP server**: fall back to `create_issue_comment` with a quoted excerpt of the original comment so the thread linkage is at least visible. Note this in the final report.
- **Validation fails after the walk**: per Step 6 — stop, print failure, do not auto-revert. User decides next step.
- **Reply post fails mid-loop**: record the failure with which comment it belonged to, continue the loop. Do not abort the whole session over one transient MCP error. List failures in the final report so the user can re-post manually.
- **User quits with `q` mid-walk**: clean stop. Still run Step 6 validation against any commits made. Still print the report. Remaining comments are reported as **not walked**, distinct from **skipped**.
- **Project has no `justfile` or no `Cargo.toml`**: Step 6 degrades per its own rules. Do not silently substitute commands.
- **`accept` is chosen but the suggested edit produces no change** (file already in the desired state): note it as "already addressed" in the report, post a reply saying so, do not create an empty commit.
- **Two reviewers contradict each other on the same code**: present both comments in turn during the walk. The user is the arbiter — don't try to merge the two views into one suggestion.

## Coexistence with `forgejo-pr-address-comments`

A bare phrase like *"address the review on PR 42"* could plausibly match either this skill or the push-through sibling. Description-line wording is what disambiguates them to the router.

- **Sibling (`forgejo-pr-address-comments`)** triggers on push-through phrasing: *"address"*, *"handle"*, *"go through and push fixes"*, *"respond to"*. Classifies and acts on the whole batch with no per-comment input.
- **This skill (`forgejo-address-pr-review`)** triggers on advisory/interactive phrasing: *"walk me through"*, *"review one by one"*, *"interactively"*, *"suggest fixes for each"*. Stops to let the user pick a disposition per comment, then acts on that choice without further confirmation.

When the routing is ambiguous, the older sibling will usually win. Users who want this skill specifically can disambiguate by phrasing (*"the interactive one"*) or by naming it explicitly.

The two skills share the same commit-message shape and validation discipline, so a PR can be handled by either skill in different rounds without inconsistency.

---
title: Answer review comments
description: Walk the comments on an open pull request one at a time with github-address-pr-review, and re-request a review only after you push a new commit.
sidebar:
  order: 3
---

This guide answers a reviewer's feedback on an open PR with
[github-address-pr-review](/pg-skills/reference/skills/github-address-pr-review/).
The skill is autonomous: it doesn't ask you anything while it runs. For each comment it
decides whether to apply a change, explain why not, or ignore the comment, and then
does it.

If you've never seen an automated review, look at one first, such as
[Brooke's review of PR #18](https://github.com/PeterGrace/pg-skills/pull/18#pullrequestreview-6005424404).
[Why a review bot](/pg-skills/explanation/review-bot/) says what each section is for.

## Steps

1. Wait for the review. On a coordinator-run epic, the coordinator messages the
   implementer that wrote the PR, and the same agent answers.
2. Ask for it: "Walk through the review comments on PR 18." The skill needs a clean
   working tree. If yours isn't, it stashes your changes, and it leaves the stash in
   place at the end.
3. Watch the narration. For each comment you'll see the reviewer, a short excerpt, the
   file and line, the decision and a one-sentence reason. It reads three sources: top-level
   conversation comments, inline review comments and non-empty review bodies. It skips
   threads already marked resolved, and it drops automated status chatter but
   keeps a bot's substantive inline review.
4. Let it apply. For an `apply` decision it makes the smallest edit, commits it with a
   message quoting the comment, and queues a reply naming the commit.
5. Let it explain. For an `explain` decision it posts a short reply saying why the code
   stays as it is, and invites the reviewer to disagree. No code changes.
6. Let it validate and push. After any commit it runs the project's gates: `just fmt`,
   `cargo clippy --all-targets -- -D warnings` if there is a `Cargo.toml`, and
   `just test`. It pushes only if they pass. It tries at most two fixes for a failure it
   caused, and otherwise stops without pushing.
7. Let it post the queued replies. It does this only after the push, and after GitHub
   can resolve each commit SHA, so the SHAs in the replies link.
8. Read the final report: counts per disposition, a table of each comment, the commit
   SHAs, the validation results and the push status.

The skill doesn't resolve threads. It posts replies only.

## Fork PRs and diverged branches

If the PR is from a fork you can't push to, or the local branch has diverged, the skill
runs in reply-only mode. Where it would have applied a change, it describes the change
in a reply for the author to apply.

## Asking for a second review

Re-request a review only after a new commit. My reviewer, Brooke, won't re-review a head
she has already reviewed. On
[PR #29](https://github.com/PeterGrace/pg-skills/pull/29) she answered a re-request on an
unchanged head with: "re-reviewing identical code would only burn tokens". The
address round there changed no code, only the description, so no second review was
possible.

Whatever reviewer you use, the rule is the same: if you pushed commits, ask again. If
you only replied, don't.

An epic's coordinator counts address rounds. After two Sonnet rounds with blocking comments
still open, Opus takes over the PR.

## Related

- [Execute an epic](/pg-skills/how-to/execute-an-epic/) says who runs this for you
  in an epic.
- A worked review round: [PR #18](https://github.com/PeterGrace/pg-skills/pull/18),
  where the review found a path traversal and a marker ordering problem, and each
  inline comment has a reply naming the commit that fixed it.

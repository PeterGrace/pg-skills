---
title: Why a review bot, and what Brooke checks
description: What I rely on a review bot for, with examples from this repository, and what to use if you don't have one.
sidebar:
  order: 3
---

Every PR in my workflow gets a review from Brooke (`brooke-reviews[bot]`), my review
bot. I approve the spec and not the plan, and the agents write the code, so the review
is where a second reader looks at what was built. This page says what I rely on
her for and what a copier can use instead.

## What you can use instead

Brooke isn't a public product, so you can't install her. Use any review bot, or a
human reviewer. What matters is the list of things below that a reviewer checks.
The skills name Brooke's login and her re-trigger command in places; the
[glossary](/pg-skills/reference/glossary/) says which names are mine.

## What I rely on her for

I rely on all four of these.

**Real bugs.** Correctness and edge cases the agent missed. On
[PR #18](https://github.com/PeterGrace/pg-skills/pull/18), the `reference` command,
her first review scored it 78 and found that an agent's frontmatter name such as
`../../README` could reach the file writer and overwrite a file outside the output
directory. The implementer fixed it with a name check and a path containment check.
Her second review found a different problem: a failed write left the output without
its ownership marker, so every retry refused to replace it. The fix writes the
marker before any page.

**Plan fidelity.** Does the PR do what the plan and the design said? Her reviews of code PRs have
a plan-fidelity section that reads the intent from the plan or design, and rates
coverage, fidelity, scope discipline and plan integrity.

**Honest PR descriptions.** She checks the description's claims against the diff.
On [PR #16](https://github.com/PeterGrace/pg-skills/pull/16) the description said
the change touched two files and needed no plan changes. The diff touched three, and
corrected the plan. She asked for the description to be fixed, and it was. On
[PR #29](https://github.com/PeterGrace/pg-skills/pull/29) the description said only
`site/` and `README.md` changed, but the PR also changed `justfile`. Neither was a
code defect.

**Security.** A blocking security finding with a low score is a trigger for
escalating a PR from Sonnet to Opus.

## Read three real reviews

All three are on PRs in this repository, so you can see what a review looks like:

- [Review on PR #18, score 78](https://github.com/PeterGrace/pg-skills/pull/18#pullrequestreview-6005424404).
  A review with a real bug. It has a quality score, an "Alignment with description"
  paragraph, then Plan fidelity, Tests, Security and Claims sections. The Security
  section is where the path-traversal finding sits, with inline comments on
  `tools/skills.py` and `tests/test_skills_tool.py` pointing at the exact lines. Its
  Tests section asks for a regression case.
- [Re-review of PR #25, score 94](https://github.com/PeterGrace/pg-skills/pull/25#pullrequestreview-6005651304).
  The review after the fix, on the milestone PR. Compare it with her
  [first review of the same PR, score 86](https://github.com/PeterGrace/pg-skills/pull/25#pullrequestreview-6005610057),
  which has the SIGPIPE finding as an inline comment on `ci.yml`.
- [Review on PR #24, score 100](https://github.com/PeterGrace/pg-skills/pull/24#pullrequestreview-6005575083).
  A clean one. The change only ticked checkboxes in the plan. The review has no
  inline comments, says "Looks fine", and has a Claims table in which what she
  couldn't check, such as test runs, is marked unverifiable.

The Claims table in each review quotes a statement from the PR description and gives
a verdict with evidence. That table is what catches an overclaiming description.

## The milestone PR gets its own review

The sub-issue reviews each see a slice. When an epic is done, the milestone PR into
`main` shows the whole thing. On
[PR #25](https://github.com/PeterGrace/pg-skills/pull/25) Brooke found the bug that
every earlier review had missed. The release step used `grep -q` in a pipeline under
`pipefail`, so a large mixed change could be misread as docs-only and skip the
release. She scored it 86. It was fixed in
[#27](https://github.com/PeterGrace/pg-skills/pull/27), and her re-review scored 94.

## The close-out audit is a second check

Brooke reviews PRs. `github-epic-close-out` reviews the epic. It checks that each
sub-issue was closed by a merged PR, that every review comment got a reply, that
each plan task's files and tests exist, and that the design's in-scope items map to
code. It finds gaps. It has caught real misses after every PR had passed review, such
as divergences nobody had documented and acceptance criteria with no test.

For the audit of epic #3, see the
[pre-merge](https://github.com/PeterGrace/pg-skills/issues/3#issuecomment-7063515563) and
[final](https://github.com/PeterGrace/pg-skills/issues/3#issuecomment-7063711827)
comments.

## Quirks worth knowing

Bots skip things. A reviewer may skip a stale branch, or miss a request, and the PR
sits. The skills handle this by reading the bot's own comments first. Brooke
declines to review a head she has already reviewed: on PR #29 she said that
re-reviewing identical code would only burn tokens. So ask again only after a new
commit.

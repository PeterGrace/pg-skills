---
title: Fact-check and reconcile a study guide
description: Run study-guide-fact-check on an existing study guide, then study-guide-reconcile to apply, reframe or defer each finding, and decide what to do with the deferred ones.
sidebar:
  order: 11
---

This guide takes a study guide that already exists and runs the second and third steps of
the loop on it: [`study-guide-fact-check`](/pg-skills/reference/skills/study-guide-fact-check/),
then [`study-guide-reconcile`](/pg-skills/reference/skills/study-guide-reconcile/). For
why the loop exists, read
[Why I fact-check generated docs](/pg-skills/explanation/why-fact-check-generated-docs/).
If you have no guide yet, the [tutorial](/pg-skills/tutorials/first-study-guide/) writes
one and runs the whole loop.

## Before you start

- The [study-guides plugin](/pg-skills/reference/plugins/study-guides/) is installed.
  The [catalog](/pg-skills/reference/dependencies/) lists no outside requirements for it
  or for these skills.
- The guide is under `docs/study-guide/` in the repository, as
  [`codebase-study-guide`](/pg-skills/reference/skills/codebase-study-guide/) writes it.
  That is the folder both skills read by default.
- You can run the fact-check on a model other than the one that wrote the guide. The
  skill says the value "comes almost entirely" from that. It doesn't name a model.

## Fact-check the guide

1. Start a Claude Code session in the repository, on a different model from the one that
   wrote the guide. In Claude Code you can change the model with `/model`.
2. Ask for the check, for example: "Fact-check the study guide in `docs/study-guide/`."
3. Let it orient itself. It reads the index, then compares the commit named in each
   doc's header with the current checkout. If they differ, it says so at the top of the
   summary, because findings may then describe code that changed after the guide was
   written, not mistakes in the guide.
4. Let it extract and test the claims. For each claim that says what the code does, it
   opens the cited file and symbol, then looks in the surrounding code for something
   that contradicts the claim. For a claim about why the code is built a certain way,
   it checks only that the claim is hedged.
5. Let it write the report. It proposes corrections and doesn't edit the guide. Its
   output goes here, and a re-run overwrites it:

   ```text
   docs/study-guide/fact-check/
   ├── SUMMARY.md
   ├── 00-architecture-overview.review.md
   ├── modules/<module-name>.review.md
   ├── glossary.review.md
   └── flashcards.review.md
   ```

6. Read `SUMMARY.md`. It has the provenance check, totals by severity and by verdict, the
   Critical findings to fix first, the items for a subject-matter expert, and the limits
   of the pass. Then read the per-doc `*.review.md` files next to the docs they review.

### What a finding says

Each finding has an id (`F1`, `F2` and so on), a verdict and a severity. The verdicts are
Verified, Contradicted, Unsupported, Stale citation, Inference-as-fact, Imprecise,
Omission and Uncheckable (SME). The severities are Critical, Moderate, Minor and Info.
Each finding also has a location, the claim, the evidence, and a suggested correction.

The skill says a Contradicted finding must point to specific code that conflicts with the
claim, and that "Unsupported" is the verdict when it can't find support but can't
disprove the claim either.

### Add your own decisions (optional)

The reconcile skill honors annotations a person has made in the review files: a finding
marked accepted or rejected, or an answer you supply for a domain question. A human
decision ranks above the skill's own re-check. The skill doesn't prescribe the
annotation's format, so write it where a reader of the finding will see it.

## Reconcile the findings

1. Ask for it, for example: "Reconcile the fact-check findings into the study guide."
   The skill doesn't require a particular model. It re-checks each finding it plans to act
   on against the code before it edits anything, so it doesn't take the report on trust. If you'd like to approve
   changes first, ask for a review gate: it then writes the reconciliation report as a
   proposal and leaves the guide untouched.
2. Let it gather and triage. It reads `SUMMARY.md` and every `*.review.md`, then sorts
   each finding into one of four actions, Critical findings first:

   | Action | Meaning | What happens to the guide |
   |--------|---------|---------------------------|
   | Apply | The code confirms the correction. | The doc is edited and its citation fixed or added. |
   | Reframe | The claim is overstated, typically an inference stated as fact. | It becomes a hedged inference or moves under Open questions. It isn't deleted. |
   | Defer | The code can't settle it. | The doc text stays as it is, with its open-question flag kept or sharpened. |
   | Reject | The code shows the original doc was right. | The doc stays, and the reason is recorded. |

3. Let it apply. It edits the guide in place under `docs/study-guide/`, adds a line
   `Revised by study-guide-reconcile on <date> from commit <short-hash>` to each changed
   doc's header, updates the Open questions sections, and updates any flashcard that
   teaches a corrected claim.
4. Read the report it writes at `docs/study-guide/fact-check/RECONCILIATION.md`. It has
   a count per outcome, then a section each for Applied, Reframed, Deferred and
   Rejected, plus the flashcards it changed and a recommended next step. Every finding
   from the fact-check is meant to appear under exactly one outcome, so compare it against
   `SUMMARY.md` to confirm that none was dropped.
5. Take the recommendation. If the edits were substantial, the skill recommends running
   the fact-check again on the revised guide, since a correction can add a new error.
   It doesn't do that itself. Repeat the fact-check steps above on the different model.

## What to do with deferred findings

Deferred findings are the ones the code couldn't settle: domain or business claims,
external systems, the report's items for a subject-matter expert, and disagreements
between the guide and the report that the code doesn't resolve. Reconcile keeps or sharpens the open-question
flag where the guide has one, and `RECONCILIATION.md` records why each was deferred and how
it was left.

You have two choices, and which one is right depends on the situation.

- **Use the guide as it is.** The deferred items stay flagged, so a reader knows which
  parts to treat with care.
- **Resolve them, now or later.** Get the answer from someone who knows (a person who
  can say whether the domain claim is right), record it as an annotation on the finding
  in the review files, and run the reconcile skill again. It applies a supplied answer
  and cites the person instead of the code.

[Why I fact-check generated docs](/pg-skills/explanation/why-fact-check-generated-docs/#how-i-finish-a-guide-that-has-open-findings)
says how I choose between them.

## Related

- [Why I fact-check generated docs](/pg-skills/explanation/why-fact-check-generated-docs/)
- [Your first study guide](/pg-skills/tutorials/first-study-guide/)
- [Audit an artifact outside a PR](/pg-skills/how-to/audit-an-artifact/), for checking
  generated docs with a claims ledger instead.

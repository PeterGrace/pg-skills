---
title: Why I fact-check generated docs
description: Why I don't trust the first draft of a generated study guide, how the write, check and reconcile loop works, why the check runs on a different model, and how I finish a guide that still has open findings.
sidebar:
  order: 5
---

When an agent writes documentation for a codebase, the result reads well whether or not
it is right. This page is about why I treat the first draft of a generated study guide as
untrusted, and what I do about it. The steps are in
[Fact-check and reconcile a study guide](/pg-skills/how-to/fact-check-a-study-guide/),
and the [tutorial](/pg-skills/tutorials/first-study-guide/) runs the whole loop on a small
repository.

## What I use study guides for

Three things: learning a codebase, being able to talk about it knowledgeably, and
onboarding other people. The
[`codebase-study-guide`](/pg-skills/reference/skills/codebase-study-guide/) skill is
written for a mixed audience, detailed enough for engineers and readable by support and
ops staff who need to reason about the system without living in the code.

The skill also produces flashcards for Anki. They are something the skill writes, not
what I use the guides for.

## The loop: write, check, reconcile

There are three skills, and each one hands its output to the next.

1. **Write.** `codebase-study-guide` reads the repository and writes the guide into
   `docs/study-guide/`: an architecture overview, a deep dive per module, a glossary and
   the flashcards, with an index that gathers every open question in one checklist.
2. **Check.** [`study-guide-fact-check`](/pg-skills/reference/skills/study-guide-fact-check/)
   reads the guide as untrusted, tries to disprove each claim about what the code does, and
   writes its findings under `docs/study-guide/fact-check/`. It proposes corrections and
   doesn't apply them. The skill says why: silently editing the docs "would erase the
   audit trail".
3. **Reconcile.** [`study-guide-reconcile`](/pg-skills/reference/skills/study-guide-reconcile/)
   takes those findings and decides what to do with each one. It applies the corrections
   the code supports, reframes the overstated claims, defers what the code can't settle
   and rejects findings that turn out to be wrong. It writes
   `docs/study-guide/fact-check/RECONCILIATION.md` so every change is on record.

The code is the arbiter in the last step, not the fact-check report. The reconcile skill
points out that the report "is still a model and still fallible", so it re-checks each
finding it plans to act on against the source before it edits anything. Sometimes the original guide was
right and the finding was wrong, and the skill treats that as a valid outcome.

## Why not trust the first draft

I have four reasons, and I hold all of them.

**Hallucinations.** Generated docs confidently describe code that doesn't exist or works
differently from what they say. The writing skill is built around this: its
core principle is to stay grounded, and it says a plausible-but-wrong doc is worse than
no doc, because people trust it. That rule makes the first draft better. It doesn't make
the draft checked.

**Circular reasoning.** A guide can cite itself, or another doc, instead of the code. It
looks right and has citations, but nothing in it is grounded. The fact-check skill
treats a citation as "a starting point to investigate, not evidence the claim is true",
and opens the cited file to see.

**Overconfidence.** Guesses get stated as facts, especially about why the code was built a
certain way. The code can't usually tell you that. The fact-check flags such a claim as
inference-as-fact, and reconcile reframes it: it rewrites the claim as a hedged inference
or moves it under the open questions, without deleting it.

**I've been burned.** Unchecked output has cost me before. I tell that story once, in
[Why audit claims](/pg-skills/explanation/why-audit-claims/#what-burned-me), and it is the
origin of this loop as well as of the claims audit.

## Why the check runs on a different model

The fact-check skill is direct about it. Its value, it says, "comes almost entirely" from
running on a different model than the one that wrote the docs, because "a model checking
its own output shares its own blind spots and tends to rationalize rather than catch its
mistakes". A fresh adversary re-derives each fact from the code.

The skill doesn't name a model for the writer or the checker. What it asks for is that
they differ. The reconcile skill assumes the same thing: it describes the fact-check as
run "(ideally) on a different model".

In practice I write with Opus and check with Sonnet. I run the check in a new Claude Code
window and switch it to Sonnet with `/model`. The new window matters too: a check run in the writer's own session would still have the writing conversation
in context.

This is a different reason from the one in my PR audits. There, my `issue-implementer`
agent runs the auditor on Sonnet, usually the same model as the implementer, to save tokens, and
the independence usually comes from a fresh context
([Why audit claims](/pg-skills/explanation/why-audit-claims/#what-gates-miss) has the
detail). For study guides, the skill's argument is about shared blind spots.

## How I finish a guide that has open findings

It depends on the situation. I either use the guide as it is, with the deferred items
still flagged, or I resolve them, now or later.

Using it as it is works because reconcile keeps or sharpens the open-question flag on a
deferred finding, and records in `RECONCILIATION.md` why it was deferred and how it was
left in the guide. The guide is usable before every finding is settled, and a reader can see which
parts aren't.

To resolve them, I need an answer the code can't give: a domain fact, or something about
an external system. The reconcile skill honors a human's decision written into the review
files, as accepted, rejected or an answer to the question. It ranks that above its own
re-check. A later reconcile run then applies the answer and cites the person rather than
the code. Which of these I do depends on the situation.

Once the edits are substantial, the skill recommends fact-checking the revised guide
again, because a correction can introduce a new error. It doesn't start that run itself.

## What this doesn't do

A fact-check is a model reading code, so it can be wrong in both directions. That is why
reconcile re-checks, and why the skill says to return **Contradicted** only when it can
point to code that conflicts with the claim. Some claims can't be settled from code at all.
Business rules and external systems go to a person, as the deferred items above. Design
rationale is hedged or moved under the open questions instead.

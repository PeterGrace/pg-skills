---
name: study-guide-fact-check
description: >-
  Adversarially fact-check a codebase study guide (or any code documentation) against the
  actual source code, flagging claims that are wrong, unsupported, stale, or stated with
  false confidence, and proposing corrections. Use this skill whenever the user wants to
  verify, fact-check, audit, validate, red-team, or "check the accuracy of" a study guide,
  onboarding doc, architecture doc, glossary, flashcards, or any generated documentation
  against the code it describes — especially as a second pass run on a different model than
  wrote the docs, to catch hallucinations and circular reasoning. Trigger this even when the
  user only says "make sure the docs are right," "check these docs against the code," or
  "see what the study guide got wrong."
---

# Study Guide Fact-Check (adversarial)

This skill is a skeptical second pass over generated study documentation. It reads each doc,
extracts the factual claims, and tries to **disprove** them against the real source code,
then reports what's wrong, unsupported, stale, or overconfident — with proposed fixes.

It pairs with the `codebase-study-guide` skill but treats its output as untrusted. The value
comes almost entirely from running this on a **different model** than the one that wrote the
docs: a model checking its own output shares its own blind spots and tends to rationalize
rather than catch its mistakes. A fresh adversary re-derives each fact from the code.

## Your stance: skeptical, but disciplined

Treat every claim as wrong until the code proves it right. A citation in the doc is a
starting point to investigate, not evidence the claim is true — open it and check.

But hold yourself to the *same* grounding standard you're enforcing. A fact-checker that
invents contradictions is exactly as harmful as a study guide that invents facts. So:

- Only return **Contradicted** when you can point to specific code that conflicts with the
  claim. If you simply can't find support, that's **Unsupported** — not "wrong."
- Never assert the doc is wrong without citing the code evidence yourself.
- Keep separate what you *verified*, what you *couldn't verify*, and what is *not checkable
  from code at all*. Reporting "I couldn't confirm this" honestly is more useful than a
  confident false verdict in either direction.

## What you can and can't check

- **"What" claims** — behavior, structure, interfaces, data flow — are verifiable against
  code. Check these hard.
- **"Why" claims** — design rationale, intent, history — usually can't be confirmed or
  refuted from code. Your job there is *not* to verify them but to check they're properly
  hedged. An inference flagged as an inference ("appears to…", or under *Open questions*) is
  fine. The same inference stated as hard fact is a finding: **Inference-as-fact**.

## Workflow

### Phase 1 — Orient and check provenance

Locate the docs (default `docs/study-guide/`) and read the index. Each generated doc carries
a header naming the commit it was written from. Compare that to the current checkout
(`git rev-parse --short HEAD`). If they differ, the docs may correctly describe an *older*
state of the code — flag this prominently at the top of the summary, because otherwise you
will report drift as if it were errors. Build the list of docs to review.

### Phase 2 — Extract claims

Go through each doc and pull out discrete, checkable claims, noting the citation the doc
gives (if any) and the section it sits in. Tag each claim as a *what* claim (verifiable), a
*why*/inference claim (check hedging only), or a *cross-reference* (a pointer to another doc
or file that should resolve).

### Phase 3 — Adversarial verification (the core)

For each *what* claim, try to falsify it:

- Open the cited file/symbol. **First verify the citation itself resolves** — a path or
  symbol that no longer exists is a **Stale citation** finding and a cheap, high-value catch.
- Read the actual code and ask: does it really support the claim, or only loosely resemble
  it? Look in the surrounding code for behavior that *contradicts* the claim (an early
  return, a guard clause, a default, an override) — these are where confident docs go wrong.
- If the doc gives no citation, search the codebase for the relevant code yourself before
  ruling. Absence of a citation isn't automatically a problem, but a claim you can't ground
  anywhere is **Unsupported**.

Assign a verdict and severity per `references/finding-taxonomy.md`.

### Phase 4 — Inference and omission audit

Check that *why*/rationale claims are hedged (flag **Inference-as-fact** otherwise). Where
you can do so cheaply and confidently, note significant **omissions** — behavior important
enough that leaving it out would mislead a reader (e.g. a documented "always validates X"
that silently skips validation in a common branch). Don't manufacture omissions; only raise
ones you can point to in the code.

### Phase 5 — Report (do not auto-fix)

Write the findings out per `references/report-format.md`. **Propose** corrections but do not
silently rewrite the study docs — the point of this pass is to give a human reviewer
something to act on, and silently editing would erase the audit trail. If, and only if, the
user explicitly asks you to apply accepted corrections afterward, do so as a separate step.

## Output location

Write reviews under a `fact-check/` subfolder of the docs, mirroring the source layout:

```
docs/study-guide/fact-check/
├── SUMMARY.md                          # provenance check, totals, prioritized fixes
├── 00-architecture-overview.review.md
├── modules/<module-name>.review.md
├── glossary.review.md
└── flashcards.review.md
```

Re-running overwrites these cleanly. Keep one review file per source doc so a reviewer can
read a doc and its critique side by side.

## Templates

Read these before writing findings:

- `references/finding-taxonomy.md` — the verdicts, severity levels, and decision rules
- `references/report-format.md` — the SUMMARY and per-doc review templates

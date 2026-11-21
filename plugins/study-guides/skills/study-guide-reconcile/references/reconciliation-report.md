# Reconciliation report

Write to `docs/study-guide/fact-check/RECONCILIATION.md`. This is the audit trail: it lets a
human see exactly what the refactor changed, confirm the judgment calls, and revert anything
they disagree with. Every finding from the fact-check should appear here under exactly one
outcome, so nothing silently disappears.

```markdown
> Reconciliation of fact-check findings into the study guide.
> Run on <YYYY-MM-DD> against commit <short-hash>.
> Mode: <applied | proposal-only>.

# Reconciliation Report

## Summary
| Outcome | Count |
|---------|-------|
| Applied | <n> |
| Reframed | <n> |
| Deferred | <n> |
| Rejected | <n> |

<One or two sentences: overall state of the docs now, and whether a re-check is recommended.>

## Applied
<Findings whose corrections were written into the docs.>
### <finding id> — <source doc> / <section>
- **Was:** <the doc's prior claim, paraphrased>
- **Now:** <the corrected claim>
- **Confirmed by:** `<file: symbol>` — <what the code shows>

## Reframed
### <finding id> — <source doc> / <section>
- **Was (asserted):** <overconfident claim>
- **Now (hedged / moved to Open questions):** <new wording>
- **Reason:** <e.g. unverifiable design rationale>

## Deferred (need a human / SME)
### <finding id> — <source doc> / <section>
- **Claim:** <paraphrase>
- **Why deferred:** <code can't settle it / domain knowledge / external system / unresolved disagreement>
- **Left in doc as:** <flagged open question | unchanged>

## Rejected (doc was right, finding was not)
### <finding id> — <source doc> / <section>
- **Finding claimed:** <what the fact-check said was wrong>
- **Why rejected:** <the code evidence that vindicates the original doc> — `<file: symbol>`

## Flashcards updated
<List any cards changed to stay consistent with corrected prose, or "none.">

## Recommended next step
<Whether to re-run study-guide-fact-check, hand the Deferred list to an SME, etc.>
```

Rules:

- **Account for every finding.** A reader of this report plus the fact-check summary should
  be able to confirm that no finding was quietly dropped.
- **Deferred and Rejected need reasons.** "Deferred" without a why, or "Rejected" without
  code evidence, is exactly the kind of unsupported assertion this whole pipeline exists to
  prevent — hold yourself to it here too.
- In **proposal-only** mode, the "Applied" and "Reframed" sections describe what *would*
  change (with the before/after wording) rather than what was changed, and the source docs
  are left untouched until a human approves.

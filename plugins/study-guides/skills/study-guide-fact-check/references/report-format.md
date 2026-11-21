# Report format

Two kinds of file: one `SUMMARY.md`, and one `*.review.md` per source doc. Findings live in
the per-doc reviews; the summary aggregates and prioritizes them.

## Per-doc review — `<source-doc>.review.md`

```markdown
> Fact-check of `<source doc path>`
> Checked on <YYYY-MM-DD> against commit <current short-hash>.
> Source doc was generated from commit <doc's stated hash> — <"same" | "DIFFERENT, see note">.

# Review: <source doc title>

## Findings

### F<n> — <verdict> (<severity>)
- **Location:** <section / heading in the source doc>
- **Claim:** <the doc's claim, paraphrased — keep it short>
- **Finding:** <what's wrong or unconfirmed, in your own words>
- **Evidence:** `<file: symbol>` — <what the code actually shows>
- **Suggested correction:** <the accurate statement, or "remove" / "add citation" / "hedge as inference">

<repeat per finding, numbered F1, F2, …>

## Spot-checks verified
<A few claims you confirmed, so the reviewer can see the doc isn't being dismissed wholesale.
Verdict: Verified. One line each.>
```

Keep finding text in your own words — paraphrase the doc's claim rather than reproducing
long passages. The **Evidence** line is the part a reviewer relies on, so always name the
concrete file and symbol.

## Summary — `SUMMARY.md`

```markdown
> Fact-check summary
> Checked on <YYYY-MM-DD> against commit <current short-hash>.

# Study Guide Fact-Check — Summary

## Provenance
<State whether the docs were generated from the same commit you checked against. If
DIFFERENT, warn clearly: some findings may reflect code that changed after the docs were
written, not doc errors. Name both hashes.>

## Totals
| Severity | Count |
|----------|-------|
| Critical | <n> |
| Moderate | <n> |
| Minor | <n> |
| Info | <n> |

By verdict: Contradicted <n>, Unsupported <n>, Stale citation <n>, Inference-as-fact <n>,
Imprecise <n>, Omission <n>, Uncheckable(SME) <n>.

Documents reviewed: <n>. <list with per-doc finding counts>

## Fix these first (Critical)
<Numbered list of the Critical findings, each one line, linking to the doc and finding ID,
e.g. "modules/auth.md F2 — claims tokens never expire; refresh_token rejects expired ones.">

## For a subject-matter expert
<The Uncheckable(SME) and unresolved-inference items gathered in one place, so the human
review has a single worklist.>

## Coverage and limits
<Briefly: what you checked, what you couldn't (e.g. external services, generated code,
areas you didn't reach), so the reader knows the bounds of this pass.>
```

The summary should let someone decide in under a minute whether the study guide is safe to
hand to the team, and exactly what to fix if not. Lead with consequences (the Critical
list), not raw counts.

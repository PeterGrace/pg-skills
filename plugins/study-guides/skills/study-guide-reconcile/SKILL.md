---
name: study-guide-reconcile
description: >-
  Reconcile the output of a study-guide fact-check with the original codebase study guide:
  triage each finding against the actual source code, apply the corrections that hold up,
  reframe overconfident claims, defer the ones that need a human, and record every change.
  Use this skill whenever the user wants to refactor, revise, update, correct, or "apply the
  fact-check to" a study guide or code documentation; incorporate review findings back into
  the docs; or close the loop after an adversarial fact-check pass. Trigger this even when
  the user only says "fix the docs based on the review," "apply the corrections," or "merge
  the fact-check findings."
---

# Study Guide Reconcile

This skill closes the loop. It takes the findings from `study-guide-fact-check`, decides
which ones actually warrant a change, and refactors the original study guide accordingly —
while leaving a clear record of what changed and why.

It is the *only* sanctioned editor of the generated study docs. Human reviewers and the
other skills don't hand-edit them; corrections flow through here so there's always an audit
trail.

## The arbiter is the code, not the report

The fact-check was run (ideally) on a different model, which makes it a useful adversary —
but it is still a model and still fallible. If this skill trusts the fact-check report as
ground truth, it just swaps one model's errors for another's. So:

- **Re-verify before you write.** Before applying any correction, confirm it against the
  source code yourself — open the file, read the symbol, check the claim. Apply the
  correction only if the *code* supports it, not merely because the report asserts it.
- **When the doc and the report disagree and the code is clear, the code wins** — and you
  may end up *rejecting* a fact-check finding because the original doc was right. Record
  that; it's a valid outcome, not a failure.
- **Defer, don't guess.** Anything the code can't settle — domain/business claims, external
  systems, the report's "for a subject-matter expert" items — is left unchanged and kept as
  a flagged open question. Never invent a resolution to make a finding go away.
- **Record every change.** A refactor with no changelog is untrustworthy; the reconciliation
  report (below) is not optional.

If SME annotations are present in the review files (a human marked findings accepted,
rejected, or supplied an answer for a domain item), honor them: an explicit human decision
outranks your own re-verification, and an SME-supplied answer is the way to resolve items
the code alone can't.

## Workflow

### Phase 1 — Gather

Read the fact-check output (default `docs/study-guide/fact-check/`): the `SUMMARY.md` and
each `*.review.md`. Build the full list of findings with their verdict, severity, location,
proposed correction, and any SME annotation. Locate the matching source docs under
`docs/study-guide/`.

### Phase 2 — Triage

Sort each finding into an action class per `references/triage-rules.md`: apply, reframe,
defer, or reject. Resolve the easy, code-verifiable ones first; the goal of triage is to
separate "the code clearly settles this" from "a human needs to decide."

### Phase 3 — Re-verify and apply

For every finding you intend to act on, re-verify against the code, then edit the source
doc. Preserve the doc's template structure and keep citations accurate — if you change a
claim, update or add the file/symbol reference that now supports it. For **Inference-as-fact**
findings, don't delete the claim; rewrite it as a properly hedged inference or move it under
*Open questions*. Leave deferred and rejected findings' doc text unchanged.

### Phase 4 — Update provenance, flags, and flashcards

- Add a revision line to each changed doc's header: `Revised by study-guide-reconcile on
  <date> from commit <short-hash>` (keep the original generation line too).
- Update the *Open questions / verify with an SME* sections: remove items now resolved, keep
  or sharpen the ones still deferred, and add anything a rejection surfaced.
- If a corrected claim is also taught by a flashcard, update the card so the deck stays
  consistent with the revised prose. A fix that leaves the flashcards contradicting the doc
  is half a fix.

### Phase 5 — Reconciliation report

Write `docs/study-guide/fact-check/RECONCILIATION.md` per
`references/reconciliation-report.md`: what was applied, reframed, deferred, and rejected
(with the reason for each rejection and deferral). This is the audit trail that lets a human
spot-check or revert your changes.

### Phase 6 — Suggest a re-check

If the edits were substantial, recommend re-running `study-guide-fact-check` on the revised
docs — a correction can introduce a new error, and a fresh adversarial pass confirms the
fixes landed. Don't run it automatically; surface it as the next step.

## Modes

Default: apply the accepted changes and write the reconciliation report. If the user asks
for a **review gate**, run Phases 1–2 and write the reconciliation report as a *proposal*
(what you would change, with diffs described) without editing the source docs, so a human
approves before anything is written.

## Output

Edits the original docs in place under `docs/study-guide/` and writes
`docs/study-guide/fact-check/RECONCILIATION.md`. Read the references before editing:

- `references/triage-rules.md` — mapping findings to actions, with the re-verify discipline
- `references/reconciliation-report.md` — the changelog format and provenance/flag updates

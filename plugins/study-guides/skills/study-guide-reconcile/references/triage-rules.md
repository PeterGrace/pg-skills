# Triage rules

Each fact-check finding gets sorted into one action. The verdict from the fact-check is a
*suggestion* for which action applies — your re-verification against the code decides. Work
the code-settleable findings first; the hard part is honestly separating "the code resolves
this" from "a human must."

## Action classes

| Action | When | What you do |
|--------|------|-------------|
| **Apply** | You re-verified against code and the correction is right. | Edit the doc to the accurate statement; fix/add the citation. |
| **Reframe** | The claim isn't false but is overstated — typically **Inference-as-fact**, or **Imprecise**. | Rewrite as a hedged inference or move under *Open questions*; don't delete a useful-but-unverifiable observation, just stop asserting it as fact. |
| **Defer** | The code can't settle it — **Uncheckable (SME)**, domain/business claims, external systems, or a doc/report disagreement you can't resolve from source. | Leave the doc text unchanged; keep or sharpen the *Open questions / verify with an SME* flag. Record it as deferred with the reason. |
| **Reject** | Re-verification shows the original doc was right and the fact-check finding was wrong. | Leave the doc unchanged; record the rejection and the code evidence that vindicates the doc. |

## The re-verify step (do this before Apply or Reframe)

For each finding you intend to act on, independently confirm it against the code — open the
cited file, read the symbol, check the surrounding logic. You are looking for one of three
outcomes:

1. **Code confirms the finding** → Apply (or Reframe) the correction as proposed.
2. **Code confirms the *original doc*, not the finding** → Reject. The fact-checker was
   wrong; the doc stays. Note this so the same finding isn't re-litigated next cycle.
3. **Code is ambiguous or silent** → Defer. Don't pick a side the code doesn't support.

Never apply a correction you couldn't independently confirm. The cost of a wrong "fix" is
high: it overwrites something that may have been correct and carries the authority of having
been "reviewed."

## Handling SME annotations

If a human has annotated the review (accepted / rejected / supplied-answer), that decision
takes precedence:

- **Accepted** → Apply, still re-verifying the wording against code where you can.
- **Rejected** → treat as Reject; leave the doc, record the human's call.
- **Supplied answer** (for a domain/SME item) → Apply using the human's answer; this is the
  intended way to resolve things the code alone can't, and you should cite the SME rather
  than the code for that claim.

## Severity and order

Resolve **Critical** findings first — these are the actively-false statements a reader would
act on. Then Moderate, then the rest. If you must stop early (large review, time/scope
limit), make sure the Critical items are all handled and say in the report what remains.

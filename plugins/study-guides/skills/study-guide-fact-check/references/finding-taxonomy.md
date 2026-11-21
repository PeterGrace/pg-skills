# Finding taxonomy

Every finding gets one **verdict** and one **severity**. The verdict says what kind of
problem it is; the severity says how much it matters. Use these consistently so the summary
counts mean something.

## Verdicts

| Verdict | Use when | Evidence required |
|---------|----------|-------------------|
| **Verified** | You confirmed the claim against the code. | The file/symbol and what it shows. (Usually you only record these for spot-checks or to show coverage — not every verified claim needs an entry.) |
| **Contradicted** | The code actively conflicts with the claim. | **Mandatory:** the specific code that conflicts. No code, no Contradicted. |
| **Unsupported** | You could not find code supporting the claim, and no citation resolves it. | Note where you looked. This is the honest verdict when you can't confirm but also can't disprove. |
| **Stale citation** | The cited file/path/symbol no longer exists or has moved. | The citation as written and the current reality. |
| **Inference-as-fact** | A *why*/rationale/intent claim is stated as hard fact without being hedged or flagged. | Quote the unhedged claim; note that it's an unverifiable inference. |
| **Imprecise** | The claim is roughly right but misleading — wrong emphasis, outdated number, sloppy wording that would cause a misunderstanding. | What's off and the accurate version. |
| **Omission** | The doc leaves out behavior important enough to mislead. | The code that should have been mentioned. |
| **Uncheckable (SME)** | The claim depends on domain/business knowledge or external systems you can't see. | Why it's out of scope; route to a subject-matter expert. |

The two verdicts to be most careful with are **Contradicted** (requires code evidence — this
is the one most likely to make *you* the source of a new error) and **Inference-as-fact**
(don't flag a properly-hedged inference; only the ones dressed as fact).

## Severity

| Severity | Meaning | Typical verdicts |
|----------|---------|------------------|
| **Critical** | A reader who trusts this will act on false information about how the system behaves. | Contradicted; high-impact Omission |
| **Moderate** | Likely to mislead or erode trust, but not an outright falsehood about behavior. | Unsupported; Inference-as-fact; some Imprecise |
| **Minor** | Small inaccuracy or staleness; worth fixing, low risk. | Stale citation; minor Imprecise |
| **Info** | Coverage notes, verified spot-checks, items routed to an SME. | Verified; Uncheckable (SME) |

Severity is about consequence to the reader, not how "wrong" something feels. A confidently
stated contradiction about a security check is Critical even if it's a one-line claim; a
stale line number is Minor even though it's flatly incorrect.

---
title: Your first study guide
description: Write a study guide for a small public Python library, fact-check it on a second model, reconcile the findings, and end with a checked guide and a report of every change.
sidebar:
  order: 2
---

In this tutorial you run the whole study-guide loop once, on a small repository you can
download. You write a guide with one skill, have a second model check it with another,
and fold the findings back in with a third. At the end you'll have a fact-checked,
reconciled guide in a local clone, and a report listing every change made to it.

The three skills are
[`codebase-study-guide`](/pg-skills/reference/skills/codebase-study-guide/),
[`study-guide-fact-check`](/pg-skills/reference/skills/study-guide-fact-check/) and
[`study-guide-reconcile`](/pg-skills/reference/skills/study-guide-reconcile/). Why the loop
has three steps is in
[Why I fact-check generated docs](/pg-skills/explanation/why-fact-check-generated-docs/).
You don't need to read it first.

## What you need

- [Claude Code](https://claude.com/claude-code), signed in, with a choice of at least two
  models. The fact-check pass should run on a different model from the one that wrote the
  guide, and step 4 does that.
- [Git](/pg-skills/reference/dependencies/#git), to clone the repository.
- Nothing else from the [dependencies page](/pg-skills/reference/dependencies/). The
  catalog lists no outside requirements for the study-guides plugin or its three skills.

## The repository you'll use

You'll write a guide for [`pallets/itsdangerous`](https://github.com/pallets/itsdangerous),
a Python library for signing data so that it can be passed through untrusted places such
as a cookie or a URL. I chose it because:

- it's public and under a permissive license, so you can clone it without an account;
- it's small: about 1,200 lines of Python in seven modules under `src/itsdangerous/`,
  few enough that the skill produces a guide in one session without asking you to pick
  what to cover. The skill asks which areas to prioritize when a codebase has more than
  about 10 to 15 modules;
- it has a tagged release, `2.2.0`, so you can check out the same code every time and
  your guide describes the same commit as the one in this tutorial;
- it already has a `docs/` folder, so you see the skill nest its output under
  `docs/study-guide/` instead of mixing it in.

You'll only read the repository. Nothing here pushes to it.

## 1. Install the plugin

In Claude Code, run these two commands. They come from the
[study-guides reference page](/pg-skills/reference/plugins/study-guides/), which has the
install commands for other clients too.

```text
/plugin marketplace add PeterGrace/pg-skills
/plugin install study-guides@pg-skills
```

If you've already added the marketplace, only the second command is new. Start a new
Claude Code session afterwards so it loads the plugin.

## 2. Clone the repository

In a terminal, in a scratch directory of your choice:

```bash
git clone --depth 1 --branch 2.2.0 --config advice.detachedHead=false https://github.com/pallets/itsdangerous itsdangerous-study
cd itsdangerous-study
git rev-parse --short HEAD
ls src/itsdangerous
```

The commit should print as `096c8d4`. The listing should show `__init__.py`, `_json.py`,
`encoding.py`, `exc.py`, `serializer.py`, `signer.py`, `timed.py`, `url_safe.py` and
`py.typed`.

## 3. Write the guide

Open Claude Code in the `itsdangerous-study` directory. Use any model you like for this
pass, and note which one you chose. Then say:

```text
Write a study guide for this codebase.
```

The skill works in phases and in order, and you'll see each of them.

1. **Reconnaissance.** It detects the language, the build system (`pyproject.toml`) and
   the layout, and looks for entry points. This is a library with no `main`, so the entry
   point is its public interface, which `src/itsdangerous/__init__.py` re-exports. It
   notes the tests and the existing `docs/`. It doesn't read every file yet.
2. **Plan and scope.** It lists the modules it found, each with a path and a one-line
   guess at its job. With about seven, it should go straight on. If it does ask what to
   prioritize, answer "all of them".
3. **Architecture overview.** It writes `00-architecture-overview.md`, built around a
   real walk of one primary path through the code, with file references at each step.
4. **Module deep dives.** One document per module, written one module at a time.
5. **Glossary.** It collects domain terms and named code constructs.
6. **Flashcards.** It derives Anki-ready cards from the documents it just wrote. You
   won't use them in this tutorial.
7. **Index and checklist.** It writes `docs/study-guide/README.md`, with a reading order
   and a checklist of every *Open questions / verify with an SME* item from all the docs.

When it finishes, look at what it wrote:

```bash
find docs/study-guide -type f | sort
```

You should see this layout. The module and flashcard file names depend on how the model
grouped the code.

```text
docs/study-guide/
├── 00-architecture-overview.md
├── README.md
├── glossary.md
├── flashcards/<module-or-topic>.txt
└── modules/<module-name>.md
```

Open `00-architecture-overview.md`. Near the top is a header with the generation date
and the commit hash, which should be `096c8d4`. Then open the checklist at the bottom of
`README.md`. These are the places where the guide itself says it isn't sure. Don't edit
any of these files by hand: the skill says corrections go through the loop, so that
there's an audit trail.

## 4. Fact-check the guide on a different model

Start a new Claude Code session in the same directory, on a different model from step 3.
You can switch with `/model`. The skills don't name a model for either pass. What they ask
for is that the two differ, because a model checking its own output shares its own blind
spots. Then say:

```text
Fact-check the study guide in docs/study-guide/.
```

You should see the skill:

1. read the index, and compare the commit in each doc's header with the current checkout.
   Both are `096c8d4`, so there's no drift warning;
2. pull out each doc's checkable claims, tagging each as a claim about what the code does,
   a claim about why, or a cross-reference;
3. try to disprove the claims about what the code does, by opening the cited file and the
   code around it;
4. check that claims about why are hedged, and note any important omissions it can point
   to in the code;
5. write the report without changing the guide.

Look at what it wrote:

```bash
find docs/study-guide/fact-check -type f | sort
```

There is a `SUMMARY.md` and one `.review.md` file for each doc, in the same layout as the
guide. Open `SUMMARY.md`. Read the provenance section, the totals by severity, and the
list under *Fix these first (Critical)*. Then open one `.review.md` and read a finding.
It has a verdict, a severity, the claim, the evidence (a file and symbol) and a suggested
correction. The review also lists a few spot-checks it verified.

The number of findings will differ from run to run. A pass can find several Critical
claims, or only Minor ones, or none. Any of those is a valid result. If it reports no
findings, the next step has little to do, and you've still run the loop.

## 5. Reconcile the findings

The reconcile step can run in the same session, or a new one. The skills don't name a
model for it, and it re-checks each finding against the code, so the choice isn't
critical. Say:

```text
Reconcile the fact-check findings into the study guide.
```

You should see the skill:

1. gather the findings from `SUMMARY.md` and the review files;
2. sort each one into apply, reframe, defer or reject, with Critical findings first;
3. re-check each finding it plans to act on against the code, then edit the guide;
4. add a revision line to each doc it changed, update the open questions, and update any
   flashcard that taught a corrected claim;
5. write `docs/study-guide/fact-check/RECONCILIATION.md`;
6. suggest a re-check if the edits were substantial.

Now check its work. Open `RECONCILIATION.md`. The summary table counts the findings per
outcome. Compare the total with the findings in `SUMMARY.md`. The report is supposed to
account for every finding under exactly one outcome.

Then find the revision lines:

```bash
grep -rn "Revised by study-guide-reconcile" docs/study-guide
```

Open one entry under *Applied*. It has what the guide said before, what it says now and
a *Confirmed by* line with a file and symbol. Open that file in `src/itsdangerous/` and
check the claim yourself. This is the habit the loop is for. If there are any entries
under *Deferred*, find the matching open question in the guide: it should still be there,
flagged, and the report says why it wasn't resolved.

## 6. Decide whether to check again

If the report recommends a re-check, you can do it now: a new session on the different
model, and the same fact-check request as step 4. It writes new review files and a new
summary. The skills don't say whether a re-run leaves `RECONCILIATION.md` in place, so
copy it somewhere outside the `fact-check/` folder first if you want to keep it.

Whether to do this, and what to do about the deferred items, is a judgment call.
[Why I fact-check generated docs](/pg-skills/explanation/why-fact-check-generated-docs/#how-i-finish-a-guide-that-has-open-findings)
says how I decide.

## What you did

You wrote a guide with one pass, had a second model try to disprove it against the code,
and applied the corrections the code supported, with a report of what changed and why. The
guide is usable now, with its deferred items still flagged.

## Next steps

- Delete the clone when you've finished with it: remove the `itsdangerous-study`
  directory.
- Do the same on a repository of your own, then use
  [Fact-check and reconcile a study guide](/pg-skills/how-to/fact-check-a-study-guide/)
  whenever you have a guide to check.
- Read [Why I fact-check generated docs](/pg-skills/explanation/why-fact-check-generated-docs/)
  for the reasons behind each step.

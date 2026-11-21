---
title: Audit an artifact outside a PR
description: Ask the claims-audit skill to check generated docs or an agent's output against the instructions it was given, and keep the findings in a claims-mcp ledger.
sidebar:
  order: 10
---

This guide audits something that isn't a pull request: generated docs, or the output of
a long agent task. It is a separate guide from
[Validate a change](/pg-skills/how-to/validate-a-change/) because the setup and the
result differ. In a PR audit, `github-issue-to-pr` runs the skill for you and the result
is a table in the PR body. Here you ask for the audit yourself, and the findings
live in a ledger. Why to do it: [Why audit claims](/pg-skills/explanation/why-audit-claims/#where-else-i-use-it).

## Before you start

- Install the [claims-audit](/pg-skills/reference/dependencies/#claims-audit) skill and
  [claims-mcp](/pg-skills/reference/dependencies/#claims-mcp), and register the server
  from the project's root. The skill requires the `claims` MCP server, because the
  verdicts are stored through its tools. The
  [install steps](/pg-skills/how-to/validate-a-change/#install) are on the other guide.
- Commit what you want audited. The server pins each piece of evidence to `HEAD`, and
  evidence recorded on uncommitted changes is marked `dirty`.
- Find the source: the brief, ticket or spec the artifact was produced from. The audit
  checks the artifact against it.

## Steps

1. Ask. The skill's description covers requests to audit, verify, validate or
   fact-check work against its instructions or spec, and to confirm that an agent
   produced what it was told to produce. For example: "Audit the guide in `docs/guide/`
   against the code it describes", or "Audit this change against the task I gave you".
   You can also run `/claims-audit`.
2. Name the source. It becomes the `source` on every claim, and when the source is a
   file in the repository, each claim also gets a `source_anchor` on the lines that
   make it.
3. Let it check for existing claims first, so a repeat audit continues instead of
   duplicating them.
4. Let it break the source into claims that are atomic, falsifiable and observable. It
   registers them as a hierarchy from the whole task down to single artifacts.
5. Let it gather evidence itself: read the code, run the tests, run the program. Each
   finding is recorded with a locator you can repeat. It records refuting findings too.
6. Read its report, which comes from `audit_report`: totals by verdict, the gap lists
   with a remediation for each, and the traceability matrix if you need one.
7. Fix what is refuted, then ask for a re-audit. The skill runs `recheck` first and
   re-audits the claims whose evidence has changed. Earlier verdicts stay in the history.

claims-mcp's [first-audit guide](https://hypotheosis.github.io/claims-mcp/guides/first-audit.html)
explains the six steps and what to expect at each, including what to check for
compound claims.

## Use a different model

The skill's core rule is that the verdict rests on evidence the auditor gathered, not on
the producer's own account. For work an agent produced, have a fresh agent do the audit,
on a different model from the one that did the work. Don't hand the auditor the
producer's summary.

## Commit the ledger

`claims.json` is meant to be committed with the code. Don't edit it by hand: each record
carries a seal, and the server refuses writes after a hand edit. If a write fails with
"was changed outside claims-mcp", stop, restore the file from git and redo the change
through the tools.

Run `claims-mcp --catalog claims.json verify` before committing. For a fixed record a
reviewer can read, claims-mcp can also
[render a PDF report](https://hypotheosis.github.io/claims-mcp/guides/reports.html).

# Flashcards — Anki-ready format

Write flashcards to `docs/study-guide/flashcards/<module-or-topic>.txt`, one file per module
or topic. Derive cards from the study docs you already wrote, so the cards stay consistent
with verified prose. Don't invent facts at the card stage.

## Format

Use a **tab-separated** file (not comma-separated — code snippets contain commas, quotes,
and braces that break CSV). Anki imports this directly. Begin the file with Anki's header
lines so import is one click with no manual field mapping:

```
#separator:tab
#html:false
#columns:Front	Back	Tags
```

Then one card per line: `Front<TAB>Back<TAB>Tags`. Tags are space-separated within the third
column (use them for the module/topic so cards can be filtered). Keep each card on a single
line — if an answer needs a code snippet, keep it short and inline; for longer explanations,
reference the doc rather than pasting a block.

**Example (tabs shown as → for illustration; use real tabs in the file):**

```
#separator:tab
#html:false
#columns:Front	Back	Tags
What is the auth module responsible for?→Issuing, validating, and refreshing session tokens; it does not store user profiles.→auth architecture
When does the session service reject a refresh token?→When it is expired or its user has been revoked (session.py: refresh_token).→auth gotchas
What does "tenant" mean in this system?→A billing-isolated customer account; all queries are scoped by tenant_id.→glossary domain
```

## What makes a good card

- **Test understanding, not trivia.** Prefer "What happens when X?" and "Why would you reach
  for Y?" over "What line is Z on?" — line numbers go stale and teach nothing.
- **One idea per card.** Split compound facts into separate cards.
- **Self-contained.** The front should make sense without the reader having the doc open.
- **Cover the high-value material:** each subsystem's responsibility, the main lifecycle
  steps, the gotchas (these make great cards), and the key glossary terms.
- **Ground them.** If a card states a specific behavior, it should trace back to something in
  the deep dives — which traces back to the code.

## Importing into Anki

Tell the user, in the README index, how to load these:
1. In Anki: **File → Import**, choose the `.txt` file.
2. Anki reads the `#separator` and `#columns` headers automatically; confirm the field
   mapping (Front, Back, Tags) and the target deck.
3. Repeat per file, or concatenate the files (keeping a single header block) to import all
   at once.

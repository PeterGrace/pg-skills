---
name: authoring-skills
description: "Adds or changes an agent skill in the PeterGrace/pg-skills repository, from SKILL.md and catalog.yaml through regenerating manifests, checks, and pushing a release. Use when asked to write, add, edit, rename or remove a skill or plugin in pg-skills, or when a change there fails `just check`."
---

# Authoring skills in pg-skills

Work in a checkout of `PeterGrace/pg-skills`. Every push to `main` that passes CI
is released automatically, so use a branch and a pull request for anything you want CI
to check before it ships.

## 1. Choose the plugin

Each plugin is an installable bundle of skills, listed in `catalog.yaml`. Add the skill
to the plugin whose topic fits. Only create a plugin if none does, and create its
directory `plugins/<plugin>/skills/` with it:

```yaml
- name: release-tools            # kebab-case; also its directory under plugins/
  description: "Skills for versioning and releasing software."   # always quoted; 1-1024 characters
  version: 0.1.0                 # semver
  category: Developer Tools      # required
  keywords: [release, semver]    # optional
  skills:
    - semver-bump
```

## 2. Write `plugins/<plugin>/skills/<skill>/SKILL.md`

```markdown
---
name: <skill>                    # must equal the directory name
description: "<what it does>. Use when <the situations that call for it>."
---

# <Title>

<Numbered steps the agent follows.>
```

- **Write the description for the agent that must choose the skill**, not for a human.
  Agents pick skills by description alone, so name the task and the trigger words a
  user would say.
- **Always wrap `description` in double quotes**, in `SKILL.md` and in `catalog.yaml`.
  In an unquoted YAML value, ` #` starts a comment, so `requests for #devops.` is
  silently cut to `requests for`. `just check` does not catch this: the shortened
  text is still valid. Escape any `"` inside the text as `\"`.
- **Write the body as instructions**: numbered steps, concrete commands, and what to
  check before finishing. Leave out background the agent doesn't need to act.
- **Keep `SKILL.md` under 500 lines.** Move long material to `references/<topic>.md`
  and link it from the step where it's needed.
- **Keep it free of secrets.** The repo is public. Naming pgrace's own bots, servers
  and conventions is fine, but give each one an entry in `GLOSSARY.md` that says what
  it is and what a reader should change.
- **Refer to other plugin skills and agents by namespaced name**
  (`github-workflows:issue-implementer`), and to the skill's own files as
  `${CLAUDE_SKILL_DIR}/...`. Never use a home-directory path such as `~/.agents/skills`.
- **A plugin can ship Claude Code subagents** as `plugins/<plugin>/agents/<agent>.md`.
  They load without any manifest entry, named `<plugin>:<agent>`.

Every frontmatter rule the validator enforces is in
[references/frontmatter.md](references/frontmatter.md). Read it before adding
`license`, `compatibility`, `metadata`, `allowed-tools` or a Claude Code key.

## 3. Scripts (only if the skill needs one)

1. Put each script in `scripts/`.
2. Python scripts need type hints on every function and must pass `mypy --strict`. Use
   the standard library only, so the script runs anywhere.
3. Add tests in `tests/skill_scripts/test_<skill>.py`, outside the skill folder so they
   aren't shipped. Load the script by path with `importlib.util.spec_from_file_location`.
4. Tell the agent in `SKILL.md` exactly how to call the script and what its output
   means.

## 4. Update the catalog and versions

1. Add the skill's name to its plugin's `skills:` list in `catalog.yaml`.
2. **Bump the plugin's `version`** for any change to its skills: patch for fixes, minor
   for new skills or behavior. Claude Code treats the version as a pin, so without a bump
   existing installs never receive the change.

## 5. Regenerate and check

```
just generate
just check
```

- **`just generate`** rewrites the generated files (`.claude-plugin/`,
  `.github/plugin/`, `.agents/plugins/`, `.cursor-plugin/`, and each plugin's
  `plugin.json` and `gemini-extension.json`). Never edit those by hand.
- **`just check`** runs validation against the Agent Skills spec and `catalog.yaml`, a
  check that the generated files are current, mypy, and the tests. It needs only `just`
  and `uv`.
- **Fix every reported error and rerun** until it passes. Error messages name the file
  and the rule.
- **The site's reference pages need nothing from you.** They are generated from the
  skill and the catalog on every deploy. Run `just site-build` if you want to see the
  page, or to check a skill's description renders cleanly.

## 6. Ship it

1. Commit the skill, `catalog.yaml` and the regenerated files together.
2. Push to `main`, or open a pull request and merge it once CI is green.

After CI passes on `main`, it tags and publishes a release, and every client that
tracks `main` picks it up.

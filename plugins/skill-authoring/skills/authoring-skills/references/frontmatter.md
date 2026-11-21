# SKILL.md and catalog rules the validator enforces

`just check` (and CI) rejects a change that breaks any rule marked **error**. The
rules live in `tools/skills.py`.

## Top-level frontmatter keys

Only the Agent Skills spec's six keys are allowed; any other top-level key is an error.

| Key | Required | Rule |
|---|---|---|
| `name` | yes | Equals the skill's directory name. 1-64 characters: lowercase `a-z`, digits and `-`. No leading, trailing or doubled `-`. Must not contain `claude` or `anthropic` (claude.ai rejects them). Unique across all plugins. |
| `description` | yes | 1-1024 characters. Says what the skill does and when to use it. Always double-quote it: unquoted, ` #` starts a YAML comment and silently truncates the text (not caught by validation). |
| `license` | no | A license name, or a bundled file such as `LICENSE.txt`. |
| `compatibility` | no | 1-500 characters. Only for real environment requirements. |
| `metadata` | no | A map of **string** keys to **string** values. Quote values such as `"1.0"` or `"true"`. |
| `allowed-tools` | no | Space-separated tools the agent may use without asking (Claude Code also takes a YAML list). Experimental. |

## Claude Code keys

Claude Code reads these extra top-level keys
([docs](https://code.claude.com/docs/en/skills)). The validator accepts them and checks
their types. Other harnesses ignore them, but **claude.ai and the Skills API reject an
upload that has any of them**, so leave them out of a skill meant for those.

| Key | Type |
|---|---|
| `when_to_use` | string, appended to `description` in the skill listing |
| `argument-hint` | string, such as `"[issue-number]"` |
| `arguments` | string or list |
| `disable-model-invocation` | `true` or `false` |
| `user-invocable` | `true` or `false` |
| `disallowed-tools` | string or list |
| `model` | string |
| `effort` | one of `low`, `medium`, `high`, `xhigh`, `max` |
| `context` | `fork` |
| `agent` | string, the subagent type used with `context: fork` |
| `background` | `true` or `false` |
| `hooks` | mapping |
| `paths` | string or list of globs |
| `shell` | `bash` or `powershell` |

## Layout

| Rule | Severity |
|---|---|
| `SKILL.md` must start with a `---` line and close its frontmatter with another | error |
| `SKILL.md` over 500 lines | warning |
| Every skill directory must be listed in `catalog.yaml`, and every listed skill must have a directory and a `SKILL.md` | error |
| Every directory under `plugins/` must be a plugin in `catalog.yaml`, and every plugin must have a directory | error |

## catalog.yaml

| Field | Rule |
|---|---|
| `schema_version` | Must be `1`. |
| `marketplace.name` | Same naming rules as skills. Must not be a name Claude Code reserves (such as `agent-skills`, `github`, or anything starting `claudeai-`). |
| `marketplace.description` | Non-empty. |
| `marketplace.owner` | `name` required, `email` optional. Also used as every plugin's author. |
| `plugins[].name` | Same naming rules as skills; equals its directory under `plugins/`. Unique. Must not be `claude`, `anthropic` and the like, or start with `claude-`, `anthropic-`, `anthropics-` or `cc-plugin-`. |
| `plugins[].description` | 1-1024 characters. Always double-quote it, for the same reason as a skill's `description`. |
| `plugins[].version` | Full semver, such as `0.1.0`. Bump it with every change to the plugin's skills. |
| `plugins[].category` | Required free text, such as `Developer Tools` or `Productivity`. |
| `plugins[].keywords` | Optional list of strings. |
| `plugins[].skills` | The skill directory names this plugin ships. |

Unknown keys anywhere in `catalog.yaml` are errors.

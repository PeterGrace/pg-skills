"""Tests for tools/skills.py, the catalog validator and manifest generator."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import textwrap
import unittest
import unittest.mock
from pathlib import Path
from types import ModuleType

TOOL = Path(__file__).resolve().parent.parent / "tools" / "skills.py"


def load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("skills_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses look the module up in sys.modules while the class body runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


skills = load_tool()

CATALOG = """\
schema_version: 1
marketplace:
  name: example-skills
  description: "Example skills."
  owner:
    name: Example Person
plugins:
  - name: release-tools
    description: "Release helpers."
    version: 1.2.0
    category: Developer Tools
    keywords: [release]
    skills:
      - semver-bump
  - name: writing
    description: "Writing helpers."
    version: 0.1.0
    category: Productivity
    skills:
      - commit-messages
"""


def skill_md(name: str, extra: str = "") -> str:
    return f'---\nname: {name}\ndescription: "Does {name}. Use when asked."\n{extra}---\n\n# Body\n'


class RepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.write("catalog.yaml", CATALOG)
        self.write("plugins/release-tools/skills/semver-bump/SKILL.md", skill_md("semver-bump"))
        self.write("plugins/writing/skills/commit-messages/SKILL.md", skill_md("commit-messages"))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, path: str, contents: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")

    def messages(self) -> list[str]:
        return [str(issue) for issue in skills.validate(self.root).issues]

    def assert_error(self, fragment: str) -> None:
        report = skills.validate(self.root)
        self.assertTrue(report.has_errors)
        self.assertTrue(
            any(fragment in str(issue) for issue in report.issues),
            f"no issue contains {fragment!r}: {self.messages()}",
        )


class ValidateTest(RepoTestCase):
    def test_valid_repo_has_no_issues(self) -> None:
        report = skills.validate(self.root)
        self.assertEqual(self.messages(), [])
        self.assertFalse(report.has_errors)

    def test_name_must_match_directory(self) -> None:
        self.write("plugins/writing/skills/commit-messages/SKILL.md", skill_md("commit-msgs"))
        self.assert_error("must equal its directory name")

    def test_unknown_top_level_key_is_an_error(self) -> None:
        self.write(
            "plugins/writing/skills/commit-messages/SKILL.md",
            skill_md("commit-messages", "version: 1\n"),
        )
        self.assert_error("unknown top-level frontmatter key 'version'")

    def test_claude_code_keys_are_accepted(self) -> None:
        extra = (
            'argument-hint: "[issue]"\ndisable-model-invocation: true\n'
            "user-invocable: false\nallowed-tools: [Read, Grep]\nmodel: sonnet\n"
            "effort: high\ncontext: fork\nagent: Explore\npaths: ['**/*.rs']\n"
            "hooks:\n  PreToolUse: []\n"
        )
        self.write(
            "plugins/writing/skills/commit-messages/SKILL.md", skill_md("commit-messages", extra)
        )
        self.assertEqual(self.messages(), [])

    def test_claude_code_key_types_are_checked(self) -> None:
        self.write(
            "plugins/writing/skills/commit-messages/SKILL.md",
            skill_md("commit-messages", 'disable-model-invocation: "yes"\n'),
        )
        self.assert_error("disable-model-invocation must be true or false")

    def test_claude_code_key_choices_are_checked(self) -> None:
        self.write(
            "plugins/writing/skills/commit-messages/SKILL.md",
            skill_md("commit-messages", "effort: extreme\n"),
        )
        self.assert_error("effort must be one of")

    def test_metadata_values_must_be_strings(self) -> None:
        self.write(
            "plugins/writing/skills/commit-messages/SKILL.md",
            skill_md("commit-messages", "metadata:\n  level: 1.0\n"),
        )
        self.assert_error("metadata.level")

    def test_reserved_skill_word_is_an_error(self) -> None:
        self.write("catalog.yaml", CATALOG.replace("commit-messages", "claude-notes"))
        self.write("plugins/writing/skills/claude-notes/SKILL.md", skill_md("claude-notes"))
        (self.root / "plugins/writing/skills/commit-messages/SKILL.md").unlink()
        (self.root / "plugins/writing/skills/commit-messages").rmdir()
        self.assert_error("which claude.ai and the API reject")

    def test_unterminated_frontmatter_is_an_error(self) -> None:
        self.write("plugins/writing/skills/commit-messages/SKILL.md", "---\nname: x\n")
        self.assert_error("never closed")

    def test_unlisted_skill_directory_is_an_error(self) -> None:
        self.write("plugins/writing/skills/stray/SKILL.md", skill_md("stray"))
        self.assert_error("'stray' is not listed")

    def test_unlisted_plugin_directory_is_an_error(self) -> None:
        self.write("plugins/orphan/skills/x/SKILL.md", skill_md("x"))
        self.assert_error("'orphan' is not in catalog.yaml")

    def test_listed_skill_without_directory_is_an_error(self) -> None:
        self.write("catalog.yaml", CATALOG + "      - missing-one\n")
        self.assert_error("'missing-one' is listed but has no directory")

    def test_duplicate_skill_across_plugins_is_an_error(self) -> None:
        self.write(
            "catalog.yaml", CATALOG.replace("      - semver-bump", "      - commit-messages")
        )
        self.assert_error("listed in both")

    def test_unknown_catalog_key_is_an_error(self) -> None:
        self.write("catalog.yaml", CATALOG.replace("    keywords:", "    tags: [x]\n    keywords:"))
        self.assert_error("unknown key 'tags'")

    def test_version_must_be_full_semver(self) -> None:
        self.write("catalog.yaml", CATALOG.replace("version: 1.2.0", "version: 1.2"))
        self.assert_error("must be a full semver string")

    def test_reserved_marketplace_name_is_an_error(self) -> None:
        self.write("catalog.yaml", CATALOG.replace("example-skills", "claudeai-tools"))
        self.assert_error("reserved by Claude Code")

    def test_long_skill_is_only_a_warning(self) -> None:
        self.write(
            "plugins/writing/skills/commit-messages/SKILL.md",
            skill_md("commit-messages") + "line\n" * 600,
        )
        report = skills.validate(self.root)
        self.assertFalse(report.has_errors)
        self.assertTrue(any("warning:" in str(issue) for issue in report.issues))


class GenerateTest(RepoTestCase):
    def generated(self) -> dict[str, str]:
        report = skills.validate(self.root)
        self.assertFalse(report.has_errors)
        files: dict[str, str] = skills.generate(report.catalog)
        return files

    def test_claude_and_copilot_share_one_format(self) -> None:
        files = self.generated()
        claude = files[".claude-plugin/marketplace.json"]
        self.assertEqual(claude, files[".github/plugin/marketplace.json"])
        expected = textwrap.dedent(
            """\
            {
              "name": "example-skills",
              "owner": {
                "name": "Example Person"
              },
              "metadata": {
                "description": "Example skills."
              },
              "plugins": [
                {
                  "name": "release-tools",
                  "source": "./plugins/release-tools",
                  "description": "Release helpers.",
                  "version": "1.2.0",
                  "author": {
                    "name": "Example Person"
                  },
                  "category": "Developer Tools",
                  "keywords": [
                    "release"
                  ]
                },
                {
                  "name": "writing",
                  "source": "./plugins/writing",
                  "description": "Writing helpers.",
                  "version": "0.1.0",
                  "author": {
                    "name": "Example Person"
                  },
                  "category": "Productivity"
                }
              ]
            }
            """
        )
        self.assertEqual(claude, expected)

    def test_writes_every_target(self) -> None:
        self.assertEqual(
            sorted(self.generated()),
            [
                ".agents/plugins/marketplace.json",
                ".claude-plugin/marketplace.json",
                ".cursor-plugin/marketplace.json",
                ".github/plugin/marketplace.json",
                "plugins/release-tools/gemini-extension.json",
                "plugins/release-tools/plugin.json",
                "plugins/writing/gemini-extension.json",
                "plugins/writing/plugin.json",
            ],
        )

    def test_agent_plugins_manifest(self) -> None:
        manifest = json.loads(self.generated()["plugins/release-tools/plugin.json"])
        self.assertEqual(manifest["$schema"], skills.AGENT_PLUGINS_SCHEMA)
        self.assertEqual(list(manifest), ["$schema", "name", "version", "description", "author", "keywords"])

    def test_check_detects_stale_and_missing_files(self) -> None:
        files = self.generated()
        self.assertEqual(skills.out_of_date(self.root, files), sorted(files))
        skills.write_files(self.root, files)
        self.assertEqual(skills.out_of_date(self.root, files), [])
        self.write(".cursor-plugin/marketplace.json", "{}\n")
        self.assertEqual(skills.out_of_date(self.root, files), [".cursor-plugin/marketplace.json"])

    def test_main_check_exit_codes(self) -> None:
        root = str(self.root)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(skills.main(["--root", root, "generate", "--check"]), 1)
            self.assertEqual(skills.main(["--root", root, "generate"]), 0)
            self.assertEqual(skills.main(["--root", root, "generate", "--check"]), 0)
            self.assertEqual(skills.main(["--root", root, "validate"]), 0)


SITE = ("example/skills", "/docs/reference")


class ReferenceTest(RepoTestCase):
    def pages(self) -> dict[str, str]:
        report = skills.validate(self.root)
        self.assertEqual(self.messages(), [])
        pages: dict[str, str] = skills.reference_pages(
            self.root, report.catalog, skills.SiteContext(*SITE)
        )
        return pages

    def test_writes_one_page_per_plugin_and_skill(self) -> None:
        self.assertEqual(
            sorted(self.pages()),
            [
                "plugins/release-tools.md",
                "plugins/writing.md",
                "skills/commit-messages.md",
                "skills/semver-bump.md",
            ],
        )

    def test_skill_page_links_plugin_and_source(self) -> None:
        text = self.pages()["skills/semver-bump.md"]
        self.assertTrue(text.startswith('---\ntitle: "semver-bump"\n'))
        self.assertIn("> Does semver-bump. Use when asked.", text)
        self.assertIn("| Plugin | [release-tools](/docs/reference/plugins/release-tools/) |", text)
        self.assertIn("| Invoke as | `release-tools:semver-bump` |", text)
        self.assertIn(
            "(https://github.com/example/skills/blob/main/"
            "plugins/release-tools/skills/semver-bump/SKILL.md)",
            text,
        )
        self.assertIn("sidebar:\n  order: 1\n", text)
        self.assertIn(skills.GENERATED_NOTE, text)

    def test_skill_page_escapes_angle_brackets(self) -> None:
        self.write(
            "plugins/release-tools/skills/semver-bump/SKILL.md",
            '---\nname: semver-bump\ndescription: "Review <pr-url> and &lt;x&gt; & co."\n---\n',
        )
        text = self.pages()["skills/semver-bump.md"]
        self.assertIn("> Review &lt;pr-url&gt; and &lt;x&gt; &amp; co.", text)
        self.assertIn('description: "Review <pr-url> and <x> & co."', text)

    def test_skill_page_lists_claude_code_settings(self) -> None:
        self.write(
            "plugins/release-tools/skills/semver-bump/SKILL.md",
            skill_md("semver-bump", "disable-model-invocation: true\n"),
        )
        text = self.pages()["skills/semver-bump.md"]
        self.assertIn("## Claude Code settings\n\n- `disable-model-invocation`: `true`", text)
        self.assertNotIn("## Claude Code settings", self.pages()["skills/commit-messages.md"])

    def test_plugin_page_lists_install_and_skills(self) -> None:
        text = self.pages()["plugins/release-tools.md"]
        self.assertIn("Release helpers.", text)
        self.assertIn("**Version** 1.2.0 · **Category** Developer Tools · **Keywords** release", text)
        self.assertIn("`/plugin install release-tools@example-skills`", text)
        self.assertIn("`copilot plugin marketplace add example/skills`", text)
        self.assertIn("`gemini extensions install ./skills/plugins/release-tools`", text)
        self.assertIn("- [semver-bump](/docs/reference/skills/semver-bump/)", text)
        self.assertNotIn("## Agents", text)
        self.assertIn("sidebar:\n  order: 1\n", text)

    def test_agent_page(self) -> None:
        self.write(
            "plugins/release-tools/agents/helper.md",
            '---\nname: helper\ndescription: "Helps."\nmodel: sonnet\n---\n\n'
            "## Rules\n\n- Be kind.\n\n```sh\n# not a heading\n```\n",
        )
        pages = self.pages()
        text = pages["agents/helper.md"]
        self.assertIn("> Helps.", text)
        self.assertIn("| Subagent type | `release-tools:helper` |", text)
        self.assertIn("| Model | `sonnet` |", text)
        self.assertIn("## Standing rules\n\n### Rules", text)
        self.assertIn("\n# not a heading\n", text)
        self.assertIn(
            "## Agents\n\n- [release-tools:helper](/docs/reference/agents/helper/)",
            pages["plugins/release-tools.md"],
        )

    def test_demote_headings_tracks_fence_marker_and_length(self) -> None:
        text = "````md\n```\n# literal\n```\n````\n## After\n~~~\n# tilde\n```\n# still tilde\n~~~\n# Out"
        self.assertEqual(
            skills.demote_headings(text),
            "````md\n```\n# literal\n```\n````\n### After\n~~~\n# tilde\n```\n# still tilde\n~~~\n## Out",
        )

    def test_duplicate_agent_names_are_an_error(self) -> None:
        agent = '---\nname: helper\ndescription: "Helps."\n---\n'
        self.write("plugins/release-tools/agents/helper.md", agent)
        self.write("plugins/writing/agents/helper.md", agent)
        report = skills.validate(self.root)
        with self.assertRaisesRegex(ValueError, "more than one plugin"):
            skills.reference_pages(self.root, report.catalog, skills.SiteContext(*SITE))

    def test_glossary_drops_its_heading(self) -> None:
        self.write("GLOSSARY.md", "# Glossary\n\nIntro.\n\n### Brooke\n\nA bot.\n")
        text = self.pages()["glossary.md"]
        self.assertTrue(text.startswith('---\ntitle: "Glossary"\n'))
        self.assertNotIn("# Glossary\n", text.split("---", 2)[2])
        self.assertIn("Intro.\n\n### Brooke\n\nA bot.", text)

    def test_write_replaces_its_own_output(self) -> None:
        out = self.root / "out"
        skills.write_reference(out, {"a.md": "1", "skills/b.md": "2"})
        skills.write_reference(out, {"c.md": "3"})
        self.assertFalse((out / "a.md").exists())
        self.assertFalse((out / "skills").exists())
        self.assertEqual((out / "c.md").read_text(encoding="utf-8"), "3")
        self.assertTrue((out / skills.GENERATED_MARKER).is_file())

    def test_write_refuses_a_directory_it_did_not_write(self) -> None:
        self.write("mine/keep.md", "x")
        with self.assertRaisesRegex(ValueError, "refusing to replace"):
            skills.write_reference(self.root / "mine", {"a.md": "1"})
        self.assertTrue((self.root / "mine/keep.md").exists())

    def test_main_reference(self) -> None:
        out = self.root / "site-ref"
        args = ["--root", str(self.root), "reference", "--out", str(out)]
        args += ["--repo", SITE[0], "--url-prefix", SITE[1]]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(skills.main(args), 0)
            self.write("plugins/writing/skills/commit-messages/SKILL.md", "no frontmatter\n")
            self.assertEqual(skills.main(args), 1)
        self.assertTrue((out / "skills/semver-bump.md").is_file())

    def reference_args(self, out: Path) -> list[str]:
        args = ["--root", str(self.root), "reference", "--out", str(out)]
        return args + ["--repo", SITE[0], "--url-prefix", SITE[1]]

    def run_main(self, args: list[str]) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code: int = skills.main(args)
        return code, err.getvalue()

    def test_agent_name_cannot_escape_the_output_directory(self) -> None:
        out = self.root / "site-ref"
        sibling = self.root / "README.md"
        sibling.write_text("keep me\n", encoding="utf-8")
        self.assertEqual(self.run_main(self.reference_args(out))[0], 0)
        before = sorted(p.relative_to(out) for p in out.rglob("*"))
        self.write(
            "plugins/release-tools/agents/evil.md",
            '---\nname: ../../README\ndescription: "Bad."\n---\n\nBody.\n',
        )
        code, err = self.run_main(self.reference_args(out))
        self.assertEqual(code, 1)
        self.assertIn("agent name", err)
        self.assertEqual(sibling.read_text(encoding="utf-8"), "keep me\n")
        self.assertEqual(sorted(p.relative_to(out) for p in out.rglob("*")), before)

    def test_write_refuses_paths_outside_the_output_before_deleting(self) -> None:
        out = self.root / "out"
        skills.write_reference(out, {"a.md": "1"})
        for bad in ("../escape.md", "sub/../../escape.md", "/abs.md"):
            with self.assertRaisesRegex(ValueError, "outside"):
                skills.write_reference(out, {"b.md": "2", bad: "x"})
            self.assertTrue((out / "a.md").is_file())
            self.assertFalse((out / "b.md").exists())
        self.assertFalse((self.root / "escape.md").exists())

    def test_main_reference_reports_a_foreign_output_directory(self) -> None:
        out = self.root / "mine"
        self.write("mine/keep.md", "x")
        code, err = self.run_main(self.reference_args(out))
        self.assertEqual(code, 1)
        self.assertIn("refusing to replace", err)
        self.assertTrue((out / "keep.md").exists())

    def test_main_reference_reports_a_malformed_agent(self) -> None:
        self.write(
            "plugins/release-tools/agents/broken.md",
            "---\nname: [unclosed\n---\n\nBody.\n",
        )
        out = self.root / "site-ref"
        code, err = self.run_main(self.reference_args(out))
        self.assertEqual(code, 1)
        self.assertIn("error:", err)
        self.assertFalse(out.exists())

    def test_main_reference_reports_a_write_failure(self) -> None:
        out = self.root / "site-ref"
        with unittest.mock.patch.object(skills, "write_reference", side_effect=OSError("disk full")):
            code, err = self.run_main(self.reference_args(out))
        self.assertEqual(code, 1)
        self.assertIn("error: disk full", err)

    def test_write_failure_midway_leaves_output_that_can_be_replaced(self) -> None:
        out = self.root / "out"
        skills.write_reference(out, {"a.md": "1"})
        real = Path.write_text

        def flaky(path: Path, *args: object, **kwargs: object) -> int:
            if path.name == "b.md":
                raise OSError("disk full")
            return real(path, *args, **kwargs)  # type: ignore[arg-type]

        with unittest.mock.patch.object(Path, "write_text", flaky):
            with self.assertRaisesRegex(OSError, "disk full"):
                skills.write_reference(out, {"a.md": "1", "b.md": "2"})
        self.assertTrue((out / skills.GENERATED_MARKER).is_file())
        skills.write_reference(out, {"a.md": "1", "b.md": "2"})
        self.assertEqual((out / "b.md").read_text(encoding="utf-8"), "2")


if __name__ == "__main__":
    unittest.main()

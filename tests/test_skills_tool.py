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


if __name__ == "__main__":
    unittest.main()

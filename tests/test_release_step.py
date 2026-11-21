"""Tests for the release step in .github/workflows/ci.yml.

The step's docs-only check ran under Actions' `bash -e -o pipefail`, where it misjudged
large mixed changes and failed diffs. These tests run the step's real `run:` script,
read out of ci.yml so it can't drift, against fake `git` and `gh` commands.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CI = REPO / ".github" / "workflows" / "ci.yml"
STEP = "Tag the next patch version and publish it"

# `git tag --points-at` prints nothing (not yet released), `git tag --list` prints the
# latest tag, and `git diff` prints the changed-path list or fails like a broken checkout.
FAKE_GIT = """#!/bin/bash
case "$1" in
  tag)
    case "$2" in
      --points-at) ;;
      --list) echo v0.1.0 ;;
    esac ;;
  diff)
    [ -n "${FAKE_DIFF_FAIL:-}" ] && { echo "fatal: bad revision" >&2; exit 128; }
    cat "$FAKE_DIFF_FILE" ;;
esac
"""
FAKE_GH = """#!/bin/bash
echo "$@" >> "$FAKE_GH_LOG"
"""


def release_script() -> str:
    workflow = yaml.safe_load(CI.read_text())
    steps = workflow["jobs"]["release"]["steps"]
    (script,) = [s["run"] for s in steps if s.get("name") == STEP]
    assert isinstance(script, str)
    return script


def nul_list(*paths: str) -> bytes:
    return b"".join(p.encode() + b"\0" for p in paths)


class ReleaseStepTest(unittest.TestCase):
    def run_step(self, diff: bytes, diff_fails: bool = False) -> tuple[int, str, str]:
        """Run the step; return (exit status, gh calls, stderr)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, body in (("git", FAKE_GIT), ("gh", FAKE_GH)):
                exe = root / name
                exe.write_text(body)
                exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
            (root / "diff").write_bytes(diff)
            env = {
                **os.environ,
                "PATH": f"{root}:{os.environ['PATH']}",
                "GITHUB_SHA": "0" * 40,
                "GH_TOKEN": "unused",
                "FAKE_DIFF_FILE": str(root / "diff"),
                "FAKE_GH_LOG": str(root / "gh.log"),
            }
            if diff_fails:
                env["FAKE_DIFF_FAIL"] = "1"
            else:
                env.pop("FAKE_DIFF_FAIL", None)
            done = subprocess.run(
                ["bash", "-e", "-o", "pipefail", "-c", release_script()],
                env=env,
                capture_output=True,
                text=True,
                cwd=root,
            )
            log = root / "gh.log"
            return done.returncode, log.read_text() if log.exists() else "", done.stderr

    def test_skills_change_releases(self) -> None:
        status, gh, _ = self.run_step(nul_list("plugins/p/SKILL.md", "docs/a.md"))
        self.assertEqual(status, 0)
        self.assertIn("release create v0.1.1", gh)

    def test_docs_only_change_is_skipped(self) -> None:
        status, gh, _ = self.run_step(nul_list("site/a.md", "docs/b.md"))
        self.assertEqual(status, 0)
        self.assertEqual(gh, "")

    def test_near_miss_prefix_releases(self) -> None:
        status, gh, _ = self.run_step(nul_list("sites/a.md"))
        self.assertEqual(status, 0)
        self.assertIn("release create", gh)

    def test_large_mixed_change_releases(self) -> None:
        # The non-docs path comes first and the rest overflows the pipe buffer, so a
        # `git diff | grep -q` pipeline would kill git with SIGPIPE.
        paths = ["tools/x"] + [f"site/page-{i}.md" for i in range(20000)]
        status, gh, _ = self.run_step(nul_list(*paths))
        self.assertEqual(status, 0)
        self.assertIn("release create v0.1.1", gh)

    def test_failed_diff_fails_the_step(self) -> None:
        status, gh, _ = self.run_step(b"", diff_fails=True)
        self.assertNotEqual(status, 0)
        self.assertEqual(gh, "")


if __name__ == "__main__":
    unittest.main()

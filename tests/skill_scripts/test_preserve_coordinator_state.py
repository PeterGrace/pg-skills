"""Tests for the github-workflows PreCompact hook, run against real temporary git repos."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[2] / "plugins" / "github-workflows" / "hooks"
SCRIPT = HOOKS / "preserve-coordinator-state.sh"


class PreserveCoordinatorStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.elsewhere = self.tmp / "elsewhere"
        self.elsewhere.mkdir()

    def run_hook(self, cwd: Path, path: str | None = None,
                 process_cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        """Runs the hook with `cwd` in the payload; the process itself starts in `process_cwd`
        (default: an unrelated directory, so only the payload can lead to the repo)."""
        env = {**os.environ}
        if path is not None:
            env["PATH"] = path
        payload = json.dumps({"hook_event_name": "PreCompact", "trigger": "auto", "cwd": str(cwd)})
        return subprocess.run(["bash", str(SCRIPT)], input=payload, capture_output=True,
                              text=True, env=env, check=False,
                              cwd=process_cwd or self.elsewhere)

    def tool_dir(self, name: str, tools: tuple[str, ...]) -> str:
        """A directory of symlinks to just `tools`, for use as PATH."""
        bin_dir = self.tmp / name
        bin_dir.mkdir()
        for tool in tools:
            found = shutil.which(tool)
            if found:
                (bin_dir / tool).symlink_to(found)
        return str(bin_dir)

    def state_dir(self) -> Path:
        d = self.repo / ".git" / "coordinator"
        d.mkdir(exist_ok=True)
        return d

    def assert_silent(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_registered_in_hooks_json(self) -> None:
        data = json.loads((HOOKS / "hooks.json").read_text())
        cmd = data["hooks"]["PreCompact"][0]["hooks"][0]
        self.assertEqual(cmd["type"], "command")
        self.assertEqual(cmd["command"], '"${CLAUDE_PLUGIN_ROOT}/hooks/preserve-coordinator-state.sh"')
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_not_a_repo(self) -> None:
        plain = self.tmp / "plain"
        plain.mkdir()
        self.assert_silent(self.run_hook(plain))

    def test_missing_directory(self) -> None:
        self.assert_silent(self.run_hook(self.tmp / "nope"))

    def test_no_git_on_path(self) -> None:
        path = self.tool_dir("nogit", ("bash", "cat", "jq", "ls", "head"))
        self.state_dir().joinpath("epic-1.md").write_text("state\n")
        self.assert_silent(self.run_hook(self.repo, path=path, process_cwd=self.repo))

    @unittest.skipUnless(shutil.which("jq"), "jq not installed")
    def test_payload_cwd_wins_over_process_cwd_with_jq(self) -> None:
        self.state_dir().joinpath("epic-1.md").write_text("payload repo state\n")
        self.assertIn("payload repo state", self.run_hook(self.repo).stdout)

    def test_without_jq_falls_back_to_process_cwd(self) -> None:
        path = self.tool_dir("nojq", ("bash", "cat", "git", "ls", "head"))
        self.state_dir().joinpath("epic-1.md").write_text("cwd repo state\n")
        result = self.run_hook(self.elsewhere, path=path, process_cwd=self.repo)
        self.assertEqual(result.returncode, 0)
        self.assertIn("cwd repo state", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_registered_command_runs_under_a_path_with_spaces(self) -> None:
        root = self.tmp / "My Plugins" / "github-workflows"
        shutil.copytree(HOOKS, root / "hooks")
        command = json.loads((HOOKS / "hooks.json").read_text())["hooks"]["PreCompact"][0]["hooks"][0]["command"]
        self.state_dir().joinpath("epic-1.md").write_text("spaced path state\n")
        payload = json.dumps({"cwd": str(self.repo)})
        result = subprocess.run(["bash", "-c", command], input=payload, capture_output=True, text=True,
                                env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(root)}, check=False,
                                cwd=self.elsewhere)
        self.assertEqual(result.returncode, 0)
        self.assertIn("spaced path state", result.stdout)

    def test_no_coordinator_directory(self) -> None:
        self.assert_silent(self.run_hook(self.repo))

    def test_empty_coordinator_directory(self) -> None:
        self.state_dir()
        self.assert_silent(self.run_hook(self.repo))

    def test_one_file(self) -> None:
        self.state_dir().joinpath("epic-7.md").write_text("PR 12 round 2 agent abc\n")
        result = self.run_hook(self.repo)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Preserve this coordinator run state verbatim", result.stdout)
        self.assertIn("PR 12 round 2 agent abc", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_from_a_linked_worktree_and_subdirectory(self) -> None:
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "--allow-empty", "-m", "x"],
                       check=True, env=env)
        wt = self.tmp / "wt"
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", str(wt), "-b", "b"],
                       check=True)
        (wt / "sub").mkdir()
        self.state_dir().joinpath("burndown-x.md").write_text("shared state\n")
        self.assertIn("shared state", self.run_hook(wt / "sub").stdout)

    def test_more_files_than_the_cap_keeps_the_newest_three(self) -> None:
        d = self.state_dir()
        for i in range(5):
            f = d / f"epic-{i}.md"
            f.write_text(f"marker-{i}\n")
            os.utime(f, (1_000_000 + i, 1_000_000 + i))
        out = self.run_hook(self.repo).stdout
        for i in (2, 3, 4):
            self.assertIn(f"marker-{i}", out)
        for i in (0, 1):
            self.assertNotIn(f"marker-{i}", out)

    def test_large_file_is_truncated(self) -> None:
        self.state_dir().joinpath("epic-big.md").write_text("A" * 100_000)
        out = self.run_hook(self.repo).stdout
        self.assertLess(len(out), 5_000)
        self.assertIn("A" * 3000, out)
        self.assertNotIn("A" * 3001, out)

    def test_total_output_is_capped_even_with_long_paths(self) -> None:
        for i in range(3):
            self.state_dir().joinpath(f"{i}-" + "n" * 200 + ".md").write_text("B" * 100_000)
        out = self.run_hook(self.repo)
        self.assertEqual(out.returncode, 0)
        self.assertLessEqual(len(out.stdout.encode()), 9500)


if __name__ == "__main__":
    unittest.main()

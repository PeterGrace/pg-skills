"""Tests for github-issue-burndown's merge-if-ready.sh, run against stub gh and git."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = (Path(__file__).resolve().parents[2] / "plugins" / "github-workflows" / "skills"
              / "github-issue-burndown" / "scripts")
SCRIPT = SCRIPT_DIR / "merge-if-ready.sh"

# Stub gh: answers the calls merge-if-ready.sh makes. The graphql answer is canned JSON that
# the script's own --jq filter runs over, so the filter is what is under test.
GH = r"""#!/usr/bin/env bash
args=("$@")
filter=
for ((i = 0; i < ${#args[@]}; i++)); do
    [ "${args[i]}" = --jq ] && filter=${args[i+1]}
done
case "$1 $2" in
    "repo view") echo main ;;
    "api graphql") jq -r "$filter" "$FIXTURE_THREADS" ;;
    "api repos/o/r/pulls/7") printf 'main\tbr\tabc123\topen\n' ;;
    "pr checks") if [ -n "$filter" ]; then echo 0; else echo "SUCCESS=1"; fi ;;
    "pr view") echo CLEAN ;;
    *) echo "unexpected gh call: $*" >&2; exit 9 ;;
esac
"""
GIT = "#!/usr/bin/env bash\nprintf 'abc123\\trefs/heads/br\\n'\n"
OK = "#!/usr/bin/env bash\necho OK\n"


def threads(*logins: tuple[str, ...]) -> str:
    """Builds a GraphQL answer: each tuple is one review thread's comment authors."""
    nodes = ",".join(
        '{"comments":{"nodes":[' + ",".join('{"author":{"login":"%s"}}' % a for a in t) + "]}}"
        for t in logins
    )
    return '{"data":{"repository":{"pullRequest":{"reviewThreads":{"nodes":[' + nodes + "]}}}}}"


class MergeIfReadyTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for name, body in (("gh", GH), ("git", GIT)):
            (self.bin / name).write_text(body)
            (self.bin / name).chmod(0o755)
        self.scripts = self.tmp / "scripts"
        self.scripts.mkdir()
        shutil.copy(SCRIPT, self.scripts / "merge-if-ready.sh")
        (self.scripts / "brooke-ok.sh").write_text(OK)
        for f in self.scripts.iterdir():
            f.chmod(0o755)

    def run_script(self, graphql: str) -> subprocess.CompletedProcess[str]:
        fixture = self.tmp / "threads.json"
        fixture.write_text(graphql)
        env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "FIXTURE_THREADS": str(fixture)}
        return subprocess.run([str(self.scripts / "merge-if-ready.sh"), "o/r", "7", "--dry-run"],
                              capture_output=True, text=True, env=env, check=False)

    def set_bot(self, login: str) -> None:
        path = self.scripts / "merge-if-ready.sh"
        text = path.read_text()
        path.write_text(re.sub(r"(?m)^bot=.*$", f"bot={login}", text))

    def test_has_a_bot_line_and_no_other_hard_coded_login(self) -> None:
        text = SCRIPT.read_text()
        self.assertEqual(re.findall(r"(?m)^bot=(\S+)$", text), ["brooke-reviews"])
        self.assertEqual(len(re.findall("brooke-reviews", text)), 1)

    def test_unreplied_thread_from_the_default_bot_refuses(self) -> None:
        result = self.run_script(threads(("brooke-reviews",)))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("1 Brooke review thread(s) have no reply", result.stdout)

    def test_replied_thread_is_ready(self) -> None:
        result = self.run_script(threads(("brooke-reviews", "someone")))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("READY (dry run)", result.stdout)

    def test_bot_line_is_honoured(self) -> None:
        self.set_bot("acme-reviewer")
        # A thread from the old default is now a human's, so it needs no reply.
        self.assertEqual(self.run_script(threads(("brooke-reviews",))).returncode, 0)
        # A thread from the new bot with no reply refuses.
        result = self.run_script(threads(("acme-reviewer",)))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("1 Brooke review thread(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()

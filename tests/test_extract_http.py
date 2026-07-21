import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import extract_http  # noqa: E402


def jl(role: str, text: str) -> str:
    return json.dumps({"message": {"role": role, "content": [{"type": "text", "text": text}]}})


class TestReadDelta(unittest.TestCase):
    def test_reads_only_new_lines_and_advances_offset(self):
        with tempfile.TemporaryDirectory() as d:
            transcript = Path(d) / "t.jsonl"
            offset = Path(d) / "t.offset"
            transcript.write_text(jl("user", "first turn") + "\n" + jl("assistant", "reply one") + "\n")

            excerpt, count = extract_http.read_delta(transcript, offset)
            self.assertIn("USER: first turn", excerpt)
            self.assertIn("ASSISTANT: reply one", excerpt)
            self.assertEqual(count, 2)

            offset.write_text("2")
            transcript.write_text(transcript.read_text() + jl("user", "second turn") + "\n")
            excerpt2, count2 = extract_http.read_delta(transcript, offset)
            self.assertIn("USER: second turn", excerpt2)
            self.assertNotIn("first turn", excerpt2)
            self.assertEqual(count2, 3)


class TestRepoName(unittest.TestCase):
    def test_falls_back_to_cwd_basename_outside_git(self):
        with tempfile.TemporaryDirectory() as d:
            repo_dir = Path(d) / "MyRepo"
            repo_dir.mkdir()
            self.assertEqual(extract_http.repo_name(str(repo_dir)), "myrepo")

    def test_strips_dot_git_and_lowercases_the_remote_basename(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            subprocess.run(
                ["git", "-C", d, "remote", "add", "origin", "https://github.com/pod/ReClaw.git"],
                check=True,
            )
            self.assertEqual(extract_http.repo_name(d), "reclaw")

    def test_empty_cwd_gives_none(self):
        self.assertIsNone(extract_http.repo_name(""))


if __name__ == "__main__":
    unittest.main()

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import context  # noqa: E402


class TestBuildBody(unittest.TestCase):
    def test_build_body_shapes_the_wire_contract(self):
        payload = {"session_id": "s-1", "prompt": "work on reclaw retrieval"}
        body = context.build_body(payload, first=True, actor="amri", repo="reclaw")
        self.assertEqual(
            body,
            {
                "actor": "amri",
                "session_id": "s-1",
                "prompt": "work on reclaw retrieval",
                "first_of_session": True,
                "repo": "reclaw",
            },
        )

    def test_build_body_carries_null_repo_outside_a_repo(self):
        payload = {"session_id": "s-1", "prompt": "p"}
        body = context.build_body(payload, first=False, actor="amri", repo=None)
        self.assertIsNone(body["repo"])


class TestMachinePrompts(unittest.TestCase):
    def test_task_notifications_and_command_wrappers_are_machine(self):
        self.assertTrue(context.is_machine_prompt(
            "<task-notification>\n<task-id>b9e3k1725</task-id>..."))
        self.assertTrue(context.is_machine_prompt(
            "  <local-command-caveat>Caveat: ...</local-command-caveat>"))
        self.assertTrue(context.is_machine_prompt("<command-name>/compact</command-name>"))

    def test_human_prompts_are_not_machine(self):
        self.assertFalse(context.is_machine_prompt("why is journaling broken"))
        self.assertFalse(context.is_machine_prompt("fix the <task-notification> renderer"))


class TestFirstOfSession(unittest.TestCase):
    def test_marker_created_once(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["POD_BRAIN_STATE_DIR"] = d
            try:
                self.assertTrue(context.is_first_of_session("abc"))
                self.assertTrue(context.is_first_of_session("abc"))  # not marked yet
                context.mark_seen("abc")
                self.assertFalse(context.is_first_of_session("abc"))  # marker now exists
                self.assertTrue(context.is_first_of_session("other"))
            finally:
                del os.environ["POD_BRAIN_STATE_DIR"]


class TestActor(unittest.TestCase):
    def test_env_override_wins_and_is_lowercased(self):
        os.environ["POD_BRAIN_ACTOR"] = "Colin"
        try:
            self.assertEqual(context.actor_name(), "colin")
        finally:
            del os.environ["POD_BRAIN_ACTOR"]


if __name__ == "__main__":
    unittest.main()

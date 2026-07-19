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
        body = context.build_body(payload, first=True, actor="amri")
        self.assertEqual(
            body,
            {
                "actor": "amri",
                "session_id": "s-1",
                "prompt": "work on reclaw retrieval",
                "first_of_session": True,
            },
        )


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

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import trigger_watch  # noqa: E402


class TestToolText(unittest.TestCase):
    def test_string_output_passes_through(self):
        self.assertEqual(trigger_watch.tool_text({"tool_output": "connection refused"}), "connection refused")

    def test_dict_output_is_flattened_to_json(self):
        text = trigger_watch.tool_text({"tool_output": {"stdout": "ECONNREFUSED"}})
        self.assertIn("ECONNREFUSED", text)

    def test_long_output_keeps_the_tail(self):
        text = trigger_watch.tool_text({"tool_output": "x" * 30000 + "THE-END"})
        self.assertEqual(len(text), trigger_watch.MAX_TEXT_CHARS)
        self.assertTrue(text.endswith("THE-END"))


class TestBuildBody(unittest.TestCase):
    def test_wire_contract(self):
        body = trigger_watch.build_body(
            {"session_id": "s-1", "tool_output": "ECONNREFUSED 127.0.0.1:6379"}, actor="amri"
        )
        self.assertEqual(
            body, {"actor": "amri", "session_id": "s-1", "text": "ECONNREFUSED 127.0.0.1:6379"}
        )

    def test_tiny_output_is_skipped(self):
        self.assertIsNone(trigger_watch.build_body({"session_id": "s-1", "tool_output": "ok"}, actor="amri"))


class TestRenderOutput(unittest.TestCase):
    def test_posttooluse_json_shape(self):
        out = trigger_watch.render_output("fire text")
        self.assertEqual(
            out,
            {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "fire text"}},
        )


if __name__ == "__main__":
    unittest.main()

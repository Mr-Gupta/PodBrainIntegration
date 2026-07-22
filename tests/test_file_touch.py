import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import file_touch  # noqa: E402


class TestBuildBody(unittest.TestCase):
    def test_shapes_the_wire_contract_from_tool_input(self):
        payload = {
            "session_id": "s-1",
            "tool_input": {"file_path": "/repo/backend/dailyMemoryService.ts"},
        }
        body = file_touch.build_body(payload, actor="amri")
        self.assertEqual(body, {
            "actor": "amri",
            "session_id": "s-1",
            "file": "/repo/backend/dailyMemoryService.ts",
        })

    def test_returns_none_without_a_file_path(self):
        self.assertIsNone(file_touch.build_body({"session_id": "s-1"}, actor="amri"))
        self.assertIsNone(file_touch.build_body(
            {"session_id": "s-1", "tool_input": {}}, actor="amri"))


class TestRenderOutput(unittest.TestCase):
    def test_wraps_context_in_hook_specific_output(self):
        out = file_touch.render_output("📁 team memory — ...")
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("team memory", out["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()

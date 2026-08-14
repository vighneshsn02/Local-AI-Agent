"""
Unit and Integration Tests for Local AI Coding Agent
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.tools import ToolRegistry
from core.memory import AgentMemory
from core.llm import ToolCallParser, OllamaClient


class TestCodingAgentComponents(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = ToolRegistry(workspace_dir=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_and_read_file(self):
        filename = "hello.py"
        content = "def greet():\n    return 'Hello, World!'\n"
        res_write = self.registry.write_file(filename, content)
        self.assertTrue(res_write.success)

        res_read = self.registry.read_file(filename)
        self.assertTrue(res_read.success)
        self.assertIn("Hello, World!", res_read.output)

    def test_edit_file(self):
        filename = "config.py"
        self.registry.write_file(filename, "PORT = 8000\nDEBUG = True\n")
        res_edit = self.registry.edit_file(filename, "PORT = 8000", "PORT = 5050")
        self.assertTrue(res_edit.success)

        res_read = self.registry.read_file(filename)
        self.assertIn("PORT = 5050", res_read.output)
        self.assertNotIn("PORT = 8000", res_read.output)

    def test_list_directory(self):
        self.registry.write_file("file1.txt", "a")
        self.registry.write_file("sub/file2.txt", "b")
        res_list = self.registry.list_directory(".")
        self.assertTrue(res_list.success)
        self.assertIn("file1.txt", res_list.output)
        self.assertIn("sub/", res_list.output)

    def test_search_code(self):
        self.registry.write_file("module.py", "def calculate_total(price, tax):\n    return price + tax\n")
        res_search = self.registry.search_code("calculate_total", ".")
        self.assertTrue(res_search.success)
        self.assertIn("module.py", res_search.output)

    def test_run_command(self):
        res_cmd = self.registry.run_command('python -c "print(10 + 25)"')
        self.assertTrue(res_cmd.success)
        self.assertIn("35", res_cmd.output)

    def test_memory_management(self):
        mem = AgentMemory(system_prompt="Test System", max_history_turns=4)
        mem.add_user_message("msg 1")
        mem.add_assistant_message("resp 1")
        mem.add_user_message("msg 2")
        mem.add_assistant_message("resp 2")
        mem.add_user_message("msg 3")

        msgs = mem.get_messages_for_llm()
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[0]["content"], "Test System")
        # System + 4 recent turns = 5 items
        self.assertEqual(len(msgs), 5)

    def test_tool_call_parser_fallback(self):
        raw_text = 'Let me read the file.\n```json\n{"tool": "read_file", "args": {"path": "main.py"}}\n```'
        cleaned, calls = ToolCallParser.parse_text_fallback(raw_text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "read_file")
        self.assertEqual(calls[0]["arguments"]["path"], "main.py")

    def test_ollama_client_status(self):
        client = OllamaClient()
        # Since Ollama is running locally, test list_models
        models = client.list_models()
        self.assertIsInstance(models, list)
        self.assertTrue(len(models) > 0)


if __name__ == "__main__":
    unittest.main()

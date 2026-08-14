"""
Core Autonomous ReAct Coding Agent.
Orchestrates LLM generation, tool execution, safety checks, multi-step problem solving, and streaming events.
"""

from typing import List, Dict, Any, Optional, Callable, Generator
import os
import json

from core.tools import ToolRegistry, OLLAMA_TOOLS_SCHEMA, ToolResult
from core.llm import OllamaClient, ToolCallParser
from core.memory import AgentMemory


DEFAULT_SYSTEM_PROMPT = """You are an expert Autonomous AI Software Engineer and Coding Assistant running locally on the user's machine.
Your purpose is to build, debug, inspect, refactor, and test code autonomously and reliably.

### Available Tools:
1. `read_file(path, start_line, end_line)`: Read source code with line numbers. ALWAYS read files before modifying them.
2. `write_file(path, content)`: Create new files or completely rewrite existing files.
3. `edit_file(path, search, replace)`: Surgically replace an exact code block in an existing file.
4. `list_directory(path)`: Inspect directory files and subdirectories.
5. `search_code(query, path, file_pattern)`: Search for function names, variables, imports, or text across the project.
6. `run_command(command, cwd, timeout)`: Run terminal commands (e.g. `python script.py`, `pytest`, `npm test`, `git status`).

### Operational Guidelines:
1. **Explore first**: When asked to modify or debug an existing project, list directories, search files, or read existing code to understand architecture.
2. **Execute tools proactively**: Do not tell the user to manually create or edit files if you can do it directly using your tools.
3. **Verify your work**: After creating or modifying code, run tests or scripts with `run_command` to verify that everything works without syntax or runtime errors.
4. **Be concise and direct**: Explain what you are doing in concise steps. After completing the task, give a clear summary of changes and how to run or test the code.
"""


class AgentEvent:
    """Represents a discrete event in the agent's reasoning/execution loop."""
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.type = event_type  # 'token', 'thought', 'tool_start', 'tool_end', 'message', 'error', 'done'
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "data": self.data}


class CodingAgent:
    """Autonomous ReAct coding agent powered by local Ollama models."""

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        model_name: str = "qwen2.5-coder:7b",
        ollama_url: str = "http://127.0.0.1:11434",
        safe_mode: bool = False,
        max_steps: int = 15,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ):
        self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())
        self.safe_mode = safe_mode
        self.max_steps = max_steps

        self.tools = ToolRegistry(workspace_dir=self.workspace_dir)
        self.llm = OllamaClient(base_url=ollama_url, default_model=model_name)
        self.memory = AgentMemory(system_prompt=system_prompt)

    def set_model(self, model_name: str):
        """Switch active local model."""
        self.llm.set_model(model_name)

    def set_safe_mode(self, enabled: bool):
        """Toggle safe confirmation mode for command executions."""
        self.safe_mode = enabled

    def get_status(self) -> Dict[str, Any]:
        """Get agent state summary."""
        return {
            "model": self.llm.model,
            "workspace": self.workspace_dir,
            "connected": self.llm.is_connected(),
            "safe_mode": self.safe_mode,
            "history_turns": self.memory.get_turn_count()
        }

    def run_stream(
        self,
        user_prompt: str,
        confirm_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    ) -> Generator[AgentEvent, None, None]:
        """
        Main multi-turn execution loop with streaming events.
        Streams thoughts, tool executions, outputs, and final responses.
        """
        # Record user message in memory
        self.memory.add_user_message(user_prompt)
        yield AgentEvent("start", {"prompt": user_prompt, "model": self.llm.model})

        step = 0
        while step < self.max_steps:
            step += 1
            yield AgentEvent("step_start", {"step": step, "max_steps": self.max_steps})

            # Fetch formatted messages for LLM
            messages = self.memory.get_messages_for_llm()

            # Stream LLM response
            accumulated_content = ""
            native_tool_calls = []

            for chunk in self.llm.chat_stream(messages=messages, tools=OLLAMA_TOOLS_SCHEMA):
                chunk_type = chunk.get("type")
                if chunk_type == "content":
                    delta = chunk.get("delta", "")
                    accumulated_content += delta
                    yield AgentEvent("token", {"delta": delta})
                elif chunk_type == "tool_calls":
                    native_tool_calls.extend(chunk.get("tool_calls", []))
                elif chunk_type == "error":
                    err_msg = chunk.get("content", "Unknown LLM error")
                    yield AgentEvent("error", {"message": err_msg})
                    return

            # Determine tool calls (native or fallback text extraction)
            extracted_tool_calls = []
            if native_tool_calls:
                extracted_tool_calls = ToolCallParser.parse_native(native_tool_calls)
            elif accumulated_content:
                cleaned_text, fallback_calls = ToolCallParser.parse_text_fallback(accumulated_content)
                if fallback_calls:
                    extracted_tool_calls = fallback_calls
                    accumulated_content = cleaned_text

            # If no tool calls were requested, the model is providing its final answer
            if not extracted_tool_calls:
                self.memory.add_assistant_message(content=accumulated_content)
                yield AgentEvent("message", {"content": accumulated_content})
                yield AgentEvent("done", {"step": step, "status": "completed"})
                return

            # Record the assistant's intention to call tools
            self.memory.add_assistant_message(
                content=accumulated_content if accumulated_content else None,
                tool_calls=native_tool_calls if native_tool_calls else None
            )

            # Execute each requested tool
            for tool_call in extracted_tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("arguments", {})

                yield AgentEvent("tool_start", {"tool": tool_name, "args": tool_args, "step": step})

                # Safe mode check for terminal commands or file modifications
                if self.safe_mode and tool_name in ("run_command", "write_file", "edit_file"):
                    if confirm_callback:
                        approved = confirm_callback(tool_name, tool_args)
                        if not approved:
                            tool_result = ToolResult(False, f"Action '{tool_name}' was aborted by user approval check.")
                            self.memory.add_tool_message(content=tool_result.output, tool_name=tool_name)
                            yield AgentEvent("tool_end", {
                                "tool": tool_name,
                                "success": False,
                                "output": tool_result.output,
                                "step": step
                            })
                            continue

                # Execute tool
                tool_result = self.tools.execute(tool_name, tool_args)

                # Record tool output in memory
                self.memory.add_tool_message(
                    content=tool_result.output,
                    tool_name=tool_name
                )

                yield AgentEvent("tool_end", {
                    "tool": tool_name,
                    "success": tool_result.success,
                    "output": tool_result.output,
                    "data": tool_result.data,
                    "step": step
                })

        # Max steps reached
        max_step_msg = f"Reached maximum allowed reasoning steps ({self.max_steps}). Summary of workspace state is available."
        yield AgentEvent("message", {"content": max_step_msg})
        yield AgentEvent("done", {"step": step, "status": "max_steps_reached"})

    def run(self, user_prompt: str) -> str:
        """Synchronous helper that executes the agent and returns final output string."""
        final_message = ""
        for event in self.run_stream(user_prompt):
            if event.type == "message":
                final_message = event.data.get("content", "")
        return final_message

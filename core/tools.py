"""
Core tools for the Local AI Coding Agent.
Provides file manipulation, code searching, directory inspection, and command execution.
"""

import os
import subprocess
import fnmatch
from typing import Dict, Any, List, Optional


class ToolResult:
    def __init__(self, success: bool, output: str, data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.output = output
        self.data = data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "data": self.data
        }

    def __str__(self) -> str:
        return self.output


class ToolRegistry:
    """Registry and execution engine for all agent tools."""

    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())

    def _resolve_path(self, path: str) -> str:
        """Resolves relative or absolute path safely within the workspace context."""
        if os.path.isabs(path):
            return os.path.abspath(path)
        return os.path.abspath(os.path.join(self.workspace_dir, path))

    def read_file(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> ToolResult:
        """Read text content from a file with optional line numbers."""
        full_path = self._resolve_path(path)
        if not os.path.exists(full_path):
            return ToolResult(False, f"Error: File '{path}' does not exist.")
        if os.path.isdir(full_path):
            return ToolResult(False, f"Error: '{path}' is a directory, not a file. Use list_directory instead.")

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            s_line = max(1, start_line or 1)
            e_line = min(total_lines, end_line or total_lines)

            if s_line > total_lines:
                return ToolResult(False, f"Error: start_line {s_line} exceeds total file lines ({total_lines}).")

            selected_lines = lines[s_line - 1 : e_line]
            formatted_output = []
            for idx, line in enumerate(selected_lines, start=s_line):
                formatted_output.append(f"{idx:4d} | {line.rstrip()}")

            header = f"=== File: {path} ({s_line}-{e_line} of {total_lines} lines) ===\n"
            content = header + "\n".join(formatted_output)
            return ToolResult(True, content, {"path": path, "total_lines": total_lines, "start_line": s_line, "end_line": e_line})
        except Exception as e:
            return ToolResult(False, f"Error reading file '{path}': {str(e)}")

    def write_file(self, path: str, content: str) -> ToolResult:
        """Write or overwrite a file with given content."""
        full_path = self._resolve_path(path)
        try:
            parent = os.path.dirname(full_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            line_count = len(content.splitlines())
            byte_size = len(content.encode("utf-8"))
            return ToolResult(
                True,
                f"Successfully wrote {byte_size} bytes ({line_count} lines) to '{path}'.",
                {"path": path, "line_count": line_count, "byte_size": byte_size}
            )
        except Exception as e:
            return ToolResult(False, f"Error writing to file '{path}': {str(e)}")

    def edit_file(self, path: str, search: str, replace: str) -> ToolResult:
        """Replace a unique code snippet within an existing file."""
        full_path = self._resolve_path(path)
        if not os.path.exists(full_path):
            return ToolResult(False, f"Error: File '{path}' does not exist.")

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            count = content.count(search)
            if count == 0:
                return ToolResult(
                    False,
                    f"Error: Target search string was not found in '{path}'. Make sure exact whitespace and characters match."
                )
            if count > 1:
                return ToolResult(
                    False,
                    f"Error: Target search string occurred {count} times in '{path}'. Please include more surrounding context to make it unique."
                )

            new_content = content.replace(search, replace, 1)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                True,
                f"Successfully updated '{path}' with the requested changes.",
                {"path": path, "replaced_length": len(search), "new_length": len(replace)}
            )
        except Exception as e:
            return ToolResult(False, f"Error editing file '{path}': {str(e)}")

    def list_directory(self, path: str = ".", max_items: int = 100) -> ToolResult:
        """List files and folders in a directory with file sizes."""
        full_path = self._resolve_path(path)
        if not os.path.exists(full_path):
            return ToolResult(False, f"Error: Directory '{path}' does not exist.")
        if not os.path.isdir(full_path):
            return ToolResult(False, f"Error: '{path}' is a file, not a directory.")

        ignored = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache", ".gemini", ".idea", ".vscode"}
        entries = []
        try:
            items = sorted(os.listdir(full_path))
            for item in items:
                if item in ignored:
                    continue
                item_full = os.path.join(full_path, item)
                is_dir = os.path.isdir(item_full)
                if is_dir:
                    try:
                        child_count = len(os.listdir(item_full))
                        entries.append(f"[DIR]  {item}/ ({child_count} items)")
                    except Exception:
                        entries.append(f"[DIR]  {item}/")
                else:
                    size = os.path.getsize(item_full)
                    size_str = f"{size} B" if size < 1024 else (f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB")
                    entries.append(f"[FILE] {item} ({size_str})")

                if len(entries) >= max_items:
                    entries.append(f"... (truncated at {max_items} items)")
                    break

            result_str = f"Directory listing of '{path}':\n" + ("\n".join(entries) if entries else "(Empty directory)")
            return ToolResult(True, result_str, {"path": path, "count": len(entries)})
        except Exception as e:
            return ToolResult(False, f"Error listing directory '{path}': {str(e)}")

    def search_code(self, query: str, path: str = ".", file_pattern: str = "*") -> ToolResult:
        """Search text or regex pattern across workspace files."""
        full_path = self._resolve_path(path)
        if not os.path.exists(full_path):
            return ToolResult(False, f"Error: Path '{path}' does not exist.")

        ignored = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache", ".gemini"}
        matches = []
        max_matches = 50

        try:
            for root, dirs, files in os.walk(full_path):
                dirs[:] = [d for d in dirs if d not in ignored]
                for file in files:
                    if not fnmatch.fnmatch(file, file_pattern):
                        continue
                    file_full = os.path.join(root, file)
                    rel_file = os.path.relpath(file_full, self.workspace_dir)
                    try:
                        with open(file_full, "r", encoding="utf-8", errors="ignore") as f:
                            for line_idx, line in enumerate(f, start=1):
                                if query.lower() in line.lower():
                                    matches.append(f"{rel_file}:{line_idx}: {line.strip()}")
                                    if len(matches) >= max_matches:
                                        break
                    except Exception:
                        continue
                    if len(matches) >= max_matches:
                        break
                if len(matches) >= max_matches:
                    break

            if not matches:
                return ToolResult(True, f"No matches found for query '{query}' in '{path}'.")

            summary = f"Found {len(matches)} match(es) for '{query}':\n" + "\n".join(matches)
            if len(matches) >= max_matches:
                summary += f"\n... (results capped at {max_matches})"
            return ToolResult(True, summary, {"query": query, "count": len(matches)})
        except Exception as e:
            return ToolResult(False, f"Error searching code for '{query}': {str(e)}")

    def run_command(self, command: str, cwd: Optional[str] = None, timeout: int = 60) -> ToolResult:
        """Execute a shell command in the workspace and return stdout and stderr."""
        exec_dir = self._resolve_path(cwd) if cwd else self.workspace_dir
        if not os.path.exists(exec_dir):
            return ToolResult(False, f"Error: Working directory '{exec_dir}' does not exist.")

        try:
            process = subprocess.run(
                command,
                shell=True,
                cwd=exec_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            stdout = process.stdout.strip()
            stderr = process.stderr.strip()
            exit_code = process.returncode

            output_lines = [f"Command: {command}", f"Exit code: {exit_code}"]
            if stdout:
                output_lines.append("--- Output ---")
                output_lines.append(stdout)
            if stderr:
                output_lines.append("--- Error output ---")
                output_lines.append(stderr)
            if not stdout and not stderr:
                output_lines.append("(No output produced)")

            full_output = "\n".join(output_lines)
            return ToolResult(exit_code == 0, full_output, {
                "command": command,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr
            })
        except subprocess.TimeoutExpired:
            return ToolResult(False, f"Error: Command '{command}' timed out after {timeout} seconds.")
        except Exception as e:
            return ToolResult(False, f"Error executing command '{command}': {str(e)}")

    def execute(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with provided arguments dictionary."""
        tools_map = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "edit_file": self.edit_file,
            "list_directory": self.list_directory,
            "search_code": self.search_code,
            "run_command": self.run_command,
        }

        if tool_name not in tools_map:
            return ToolResult(False, f"Error: Unknown tool '{tool_name}'. Available tools: {', '.join(tools_map.keys())}")

        try:
            return tools_map[tool_name](**args)
        except TypeError as te:
            return ToolResult(False, f"Error calling '{tool_name}' with arguments {args}: {str(te)}")
        except Exception as e:
            return ToolResult(False, f"Unexpected error executing '{tool_name}': {str(e)}")


# Schemas for Ollama / LLM Tool Calling
OLLAMA_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file with line numbers. Use this before modifying any code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative or absolute path to the file."},
                    "start_line": {"type": "integer", "description": "Optional starting line number (1-indexed)."},
                    "end_line": {"type": "integer", "description": "Optional ending line number (1-indexed)."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or completely overwrite an existing file with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the target file."},
                    "content": {"type": "string", "description": "The exact full text content to write."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a unique code snippet inside an existing file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to edit."},
                    "search": {"type": "string", "description": "The exact existing text chunk to find and replace."},
                    "replace": {"type": "string", "description": "The new replacement text chunk."}
                },
                "required": ["path", "search", "replace"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories in a directory path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list (default is '.')"},
                    "max_items": {"type": "integer", "description": "Maximum number of items to return (default 100)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a keyword or text pattern across files in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or substring to find."},
                    "path": {"type": "string", "description": "Directory to search within (default '.')"},
                    "file_pattern": {"type": "string", "description": "Glob pattern for filenames (e.g. '*.py', '*.js')"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a terminal shell command (e.g. running python scripts, tests, pip installs, or compilers).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The exact shell command to execute."},
                    "cwd": {"type": "string", "description": "Optional working directory for the command."},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 60)."}
                },
                "required": ["command"]
            }
        }
    }
]

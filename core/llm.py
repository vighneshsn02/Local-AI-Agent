"""
LLM interface for local Ollama models.
Handles model discovery, streaming chat completions, native function calling,
and robust fallback extraction for local coding models.
"""

import json
import re
import requests
from typing import List, Dict, Any, Optional, Generator, Tuple
from core.tools import OLLAMA_TOOLS_SCHEMA


class OllamaClient:
    """Client for communicating with a local Ollama instance."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", default_model: str = "qwen2.5-coder:7b"):
        self.base_url = base_url.rstrip("/")
        self.model = default_model

    def is_connected(self) -> bool:
        """Check if local Ollama daemon is reachable."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[Dict[str, Any]]:
        """Fetch list of all installed local models."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code == 200:
                data = r.json()
                models = []
                for m in data.get("models", []):
                    size_gb = m.get("size", 0) / (1024 ** 3)
                    models.append({
                        "name": m.get("name", ""),
                        "size": f"{size_gb:.1f} GB" if size_gb > 0 else "N/A",
                        "modified_at": m.get("modified_at", ""),
                        "details": m.get("details", {})
                    })
                return models
        except Exception:
            pass
        return []

    def set_model(self, model_name: str):
        """Change active model."""
        self.model = model_name

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream chat completion from Ollama.
        Yields chunk dictionaries containing token strings and/or tool calls.
        """
        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": 16384  # Expanded context window for coding
            }
        }
        if tools:
            payload["tools"] = tools

        try:
            with requests.post(url, json=payload, stream=True, timeout=120) as response:
                if response.status_code != 200:
                    yield {
                        "type": "error",
                        "content": f"Ollama API error ({response.status_code}): {response.text}"
                    }
                    return

                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                            msg = chunk.get("message", {})
                            content = msg.get("content", "")
                            tool_calls = msg.get("tool_calls", [])
                            done = chunk.get("done", False)

                            if content:
                                yield {"type": "content", "delta": content}
                            if tool_calls:
                                yield {"type": "tool_calls", "tool_calls": tool_calls}
                            if done:
                                yield {"type": "done", "total_duration": chunk.get("total_duration")}
                        except Exception:
                            continue
        except requests.exceptions.ConnectionError:
            yield {
                "type": "error",
                "content": f"Could not connect to Ollama at {self.base_url}. Please ensure Ollama is running (`ollama serve`)."
            }
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Error during streaming generation: {str(e)}"
            }

    def chat_non_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """Non-streaming chat completion."""
        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 16384
            }
        }
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(url, json=payload, timeout=180)
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {})
            return {"content": f"Ollama Error {response.status_code}: {response.text}"}
        except Exception as e:
            return {"content": f"Connection Error: {str(e)}"}


class ToolCallParser:
    """
    Parses tool calls from LLM outputs.
    Supports both native structured tool_calls AND text-based XML/JSON blocks.
    """

    @staticmethod
    def parse_native(tool_calls_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parses native Ollama tool_calls array."""
        parsed = []
        for call in tool_calls_data:
            func = call.get("function", {})
            name = func.get("name", "")
            args = func.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            if name:
                parsed.append({"name": name, "arguments": args})
        return parsed

    @staticmethod
    def parse_text_fallback(content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parses text for embedded tool calls like:
        <tool_call name="read_file">
        {"path": "app.py"}
        </tool_call>
        or
        ```json
        {"tool": "write_file", "path": "main.py", "content": "..."}
        ```
        Returns cleaned conversational text and list of parsed tool calls.
        """
        tool_calls = []
        cleaned_text = content

        # 1. Look for <tool_call name="...">...</tool_call>
        xml_pattern = r'<tool_call\s+name=["\']([^"\']+)["\']>(.*?)</tool_call>'
        matches = list(re.finditer(xml_pattern, content, re.DOTALL))
        for m in matches:
            tool_name = m.group(1).strip()
            raw_args = m.group(2).strip()
            args = {}
            try:
                args = json.loads(raw_args)
            except Exception:
                # Try simple key-value extraction
                kv_matches = re.findall(r'<(\w+)>(.*?)</\1>', raw_args, re.DOTALL)
                for k, v in kv_matches:
                    args[k] = v.strip()
            if tool_name:
                tool_calls.append({"name": tool_name, "arguments": args})

        if tool_calls:
            cleaned_text = re.sub(xml_pattern, "", content, flags=re.DOTALL).strip()
            return cleaned_text, tool_calls

        # 2. Look for JSON code blocks or raw JSON containing tool calls
        known_tools = {"read_file", "write_file", "edit_file", "list_directory", "search_code", "run_command"}
        json_code_blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        
        # If no markdown block, check if whole content or substring is a JSON object
        candidate_blocks = list(json_code_blocks)
        if not candidate_blocks:
            raw_match = re.search(r'(\{[\s\S]*\})', content)
            if raw_match:
                candidate_blocks.append(raw_match.group(1))

        for block in candidate_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, dict):
                    tool_name = data.get("name") or data.get("tool") or data.get("function") or data.get("action")
                    if tool_name in known_tools or (isinstance(tool_name, str) and tool_name.strip() in known_tools):
                        tool_name = tool_name.strip()
                        args = data.get("args") or data.get("arguments") or data.get("parameters") or {}
                        if not args or not isinstance(args, dict):
                            # Use remaining keys as args
                            args = {k: v for k, v in data.items() if k not in ("tool", "function", "action", "name")}
                        tool_calls.append({"name": tool_name, "arguments": args})
            except Exception:
                continue

        if tool_calls:
            for block in candidate_blocks:
                cleaned_text = cleaned_text.replace(f"```json\n{block}\n```", "").replace(f"```{block}```", "").replace(block, "").strip()

        return cleaned_text, tool_calls

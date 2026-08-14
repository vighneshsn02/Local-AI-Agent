"""
Conversation memory and context window management for the Coding Agent.
Handles message history, sliding context windows, and tool result caching.
"""

from typing import List, Dict, Any, Optional
import json


class AgentMemory:
    """Manages chat conversation history and token bounds."""

    def __init__(self, system_prompt: str, max_history_turns: int = 30):
        self.system_prompt = system_prompt
        self.max_history_turns = max_history_turns
        self.messages: List[Dict[str, Any]] = []

    def set_system_prompt(self, new_prompt: str):
        """Update system prompt."""
        self.system_prompt = new_prompt

    def add_user_message(self, content: str) -> Dict[str, Any]:
        """Record user message."""
        msg = {"role": "user", "content": content}
        self.messages.append(msg)
        return msg

    def add_assistant_message(self, content: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Record assistant response, including optional tool calls."""
        msg: Dict[str, Any] = {"role": "assistant"}
        if content is not None:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)
        return msg

    def add_tool_message(self, content: str, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Record tool output message."""
        msg: Dict[str, Any] = {
            "role": "tool",
            "content": content
        }
        if tool_name:
            msg["name"] = tool_name
        self.messages.append(msg)
        return msg

    def get_messages_for_llm(self) -> List[Dict[str, Any]]:
        """
        Constructs the message payload for the LLM request.
        Always places system prompt first, followed by truncated recent history.
        """
        payload = [{"role": "system", "content": self.system_prompt}]

        # Keep last max_history_turns messages to avoid overflowing local model context windows
        recent_msgs = self.messages[-self.max_history_turns:] if len(self.messages) > self.max_history_turns else self.messages

        # Add recent messages
        payload.extend(recent_msgs)
        return payload

    def clear(self):
        """Clear all conversation turns while preserving system prompt."""
        self.messages.clear()

    def get_turn_count(self) -> int:
        """Returns the number of user/assistant turns."""
        return len([m for m in self.messages if m.get("role") in ("user", "assistant")])

    def export_json(self) -> str:
        """Export history to JSON string."""
        return json.dumps({
            "system_prompt": self.system_prompt,
            "messages": self.messages
        }, indent=2)

    def load_json(self, data_str: str):
        """Load history from JSON string."""
        data = json.loads(data_str)
        self.system_prompt = data.get("system_prompt", self.system_prompt)
        self.messages = data.get("messages", [])

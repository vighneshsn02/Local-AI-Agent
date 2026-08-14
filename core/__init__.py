"""
Local Coding AI Agent Core Package
"""
from core.agent import CodingAgent, AgentEvent, DEFAULT_SYSTEM_PROMPT
from core.tools import ToolRegistry, ToolResult, OLLAMA_TOOLS_SCHEMA
from core.llm import OllamaClient, ToolCallParser
from core.memory import AgentMemory

__all__ = [
    "CodingAgent",
    "AgentEvent",
    "DEFAULT_SYSTEM_PROMPT",
    "ToolRegistry",
    "ToolResult",
    "OLLAMA_TOOLS_SCHEMA",
    "OllamaClient",
    "ToolCallParser",
    "AgentMemory"
]

"""
Web Server for the Local Coding AI Agent.
Provides REST APIs and Server-Sent Events (SSE) streaming for the Web Dashboard.
"""

import os
import sys
import json
import queue
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
from flask_cors import CORS

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.agent import CodingAgent, AgentEvent


app = Flask(__name__, static_folder="static", template_folder="static")
CORS(app)

# Global Agent Instance
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
agent = CodingAgent(workspace_dir=WORKSPACE_ROOT, model_name="qwen2.5-coder:7b", safe_mode=False)


@app.route("/")
def index():
    """Serve main single-page application."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get current agent status and configuration."""
    status = agent.get_status()
    models = agent.llm.list_models()
    return jsonify({
        "status": "ok",
        "agent": status,
        "available_models": models
    })


@app.route("/api/models", methods=["GET"])
def list_models():
    """List all installed local models."""
    models = agent.llm.list_models()
    return jsonify({
        "current_model": agent.llm.model,
        "models": models
    })


@app.route("/api/models/switch", methods=["POST"])
def switch_model():
    """Switch active local model."""
    data = request.get_json() or {}
    model_name = data.get("model")
    if not model_name:
        return jsonify({"error": "Missing model name"}), 400

    agent.set_model(model_name)
    return jsonify({
        "success": True,
        "current_model": agent.llm.model
    })


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update settings like safe mode or workspace directory."""
    data = request.get_json() or {}
    if "safe_mode" in data:
        agent.set_safe_mode(bool(data["safe_mode"]))
    if "workspace" in data and os.path.isdir(data["workspace"]):
        agent.workspace_dir = os.path.abspath(data["workspace"])
        agent.tools.workspace_dir = agent.workspace_dir
    return jsonify({"success": True, "agent": agent.get_status()})


@app.route("/api/clear", methods=["POST"])
def clear_memory():
    """Clear conversation history."""
    agent.memory.clear()
    return jsonify({"success": True, "message": "Conversation memory reset"})


@app.route("/api/workspace/tree", methods=["GET"])
def get_workspace_tree():
    """Return file tree structure of the workspace."""
    workspace = agent.workspace_dir
    ignored = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache", ".gemini", ".idea", ".vscode"}

    def build_tree(path: str, max_depth: int = 4, current_depth: int = 0) -> Dict[str, Any]:
        if current_depth > max_depth:
            return {"name": os.path.basename(path), "type": "directory", "children": []}

        name = os.path.basename(path) or path
        if os.path.isdir(path):
            children = []
            try:
                for item in sorted(os.listdir(path)):
                    if item in ignored:
                        continue
                    item_path = os.path.join(path, item)
                    children.append(build_tree(item_path, max_depth, current_depth + 1))
            except Exception:
                pass
            return {
                "name": name,
                "path": os.path.relpath(path, workspace),
                "type": "directory",
                "children": children
            }
        else:
            size = os.path.getsize(path) if os.path.exists(path) else 0
            return {
                "name": name,
                "path": os.path.relpath(path, workspace),
                "type": "file",
                "size": size
            }

    tree = build_tree(workspace)
    return jsonify({"workspace": workspace, "tree": tree})


@app.route("/api/workspace/file", methods=["GET"])
def get_file_content():
    """Fetch content of a file in the workspace."""
    file_path = request.args.get("path")
    if not file_path:
        return jsonify({"error": "Missing file path"}), 400

    full_path = os.path.abspath(os.path.join(agent.workspace_dir, file_path))
    if not os.path.exists(full_path) or os.path.isdir(full_path):
        return jsonify({"error": "File does not exist or is a directory"}), 404

    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return jsonify({
            "path": file_path,
            "content": content,
            "size": len(content)
        })
    except Exception as e:
        return jsonify({"error": f"Error reading file: {str(e)}"}), 500


@app.route("/api/workspace/save", methods=["POST"])
def save_file():
    """Save content to a workspace file."""
    data = request.get_json() or {}
    file_path = data.get("path")
    content = data.get("content")

    if not file_path or content is None:
        return jsonify({"error": "Missing path or content"}), 400

    res = agent.tools.write_file(file_path, content)
    return jsonify(res.to_dict())


@app.route("/api/terminal/exec", methods=["POST"])
def exec_terminal():
    """Execute a manual terminal command in the workspace."""
    data = request.get_json() or {}
    command = data.get("command", "")
    if not command:
        return jsonify({"error": "Missing command"}), 400

    res = agent.tools.run_command(command)
    return jsonify(res.to_dict())


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """
    Stream agent execution events over Server-Sent Events (SSE).
    """
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    def event_stream():
        try:
            for event in agent.run_stream(prompt):
                event_payload = json.dumps(event.to_dict())
                yield f"data: {event_payload}\n\n"
        except Exception as e:
            err_payload = json.dumps({"type": "error", "data": {"message": str(e)}})
            yield f"data: {err_payload}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


def start_server(port: int = 5050, host: str = "127.0.0.1", debug: bool = False):
    """Start the Flask Web App."""
    print(f"\n=======================================================")
    print(f"  ⚡ Local Coding AI Agent Web UI running at:")
    print(f"  👉 http://{host}:{port}")
    print(f"=======================================================\n")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    start_server(port=5050)

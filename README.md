# ⚡ Local AI Coding Agent

An autonomous, full-featured AI software engineering agent that runs **100% locally on your computer** using **Ollama** models (such as `qwen2.5-coder:7b`, `qwen2.5-coder:3b`, `llama3.2:3b`, `deepseek-coder`, etc.). No external API keys or cloud connections required.

---

## 🌟 Highlights

- **100% Local & Private**: All model inference, code analysis, and tool executions stay strictly inside your machine.
- **Dual Interface**:
  - 🖥️ **Interactive Rich Terminal CLI**: Real-time token streaming, slash commands (`/model`, `/files`, `/safe`, `/clear`), syntax highlighting, and expandable tool execution panels.
  - 🌐 **Modern Web UI**: Real-time Server-Sent Events (SSE) chat, project file explorer tree, built-in code editor/diff viewer, model switcher, and one-click quick actions.
- **Autonomous Multi-Step ReAct Loop**:
  - 📖 `read_file`: Inspects files with line numbers.
  - ✏️ `write_file`: Creates or replaces code files with automatic directory creation.
  - 🔬 `edit_file`: Performs surgical search-and-replace edits.
  - 📁 `list_directory`: Traverses workspace folders.
  - 🔎 `search_code`: Fast text and pattern searching across files.
  - ⚡ `run_command`: Runs terminal commands (tests, builds, scripts) and captures output.
- **Safety Safeguards**: Optional *Safe Mode* that prompts you for confirmation before executing shell commands or modifying files.
- **Universal Model Compatibility**: Supports both native Ollama function-calling models and text-based fallback parsing for smaller local models (3B / 1.3B).

---

## 🚀 Quick Start

### 1. Requirements
- **Python 3.10+** (Python 3.13 is supported)
- **Ollama** installed and running (`ollama serve`)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launching the Agent

#### Option A: Launch Web UI (Recommended)
Double-click `run_web.bat` or run:
```bash
python main.py web --port 5050
```
Open **[http://127.0.0.1:5050](http://127.0.0.1:5050)** in your web browser.

#### Option B: Launch Interactive Terminal CLI
Double-click `run_cli.bat` or run:
```bash
python main.py cli
```

---

## 🎮 CLI Slash Commands

Inside the interactive terminal CLI, you can use the following commands:

| Command | Description |
|---|---|
| `/model` | Switch the active local Ollama model interactively |
| `/models` | List all installed Ollama models and disk sizes |
| `/safe` | Toggle Safe Confirmation Mode on/off |
| `/files` | Print workspace file tree |
| `/read <path>` | Read and display a file with line numbers |
| `/clear` | Clear conversation memory and reset context |
| `/status` | View current agent configuration and connection |
| `/help` | Display command cheat sheet |
| `/exit` or `quit` | Exit the CLI |

---

## 🏗️ Architecture

```
D:/vighneshnaik/
├── core/
│   ├── agent.py          # Multi-turn ReAct reasoning loop & streaming events
│   ├── llm.py            # Ollama API client & dual-mode tool parser
│   ├── tools.py          # Safe file, search, directory, and terminal tools
│   └── memory.py         # Conversation history & context window manager
├── cli/
│   └── main.py           # Interactive Rich Terminal UI & slash commands
├── web/
│   ├── app.py            # Flask backend (SSE streaming & workspace REST API)
│   └── static/
│       ├── index.html    # Single-page web dashboard
│       ├── app.css       # Clean dark-mode design system
│       └── app.js        # SSE stream consumer, file tree, code viewer
├── tests/
│   └── test_agent.py     # Automated unit & integration tests
├── main.py               # Unified CLI/Web launcher
├── run_cli.bat           # 1-click CLI batch runner
├── run_web.bat           # 1-click Web UI batch runner
└── requirements.txt      # Python dependencies
```

---

## 🧪 Running Tests

To run the automated test suite:
```bash
python -m unittest tests/test_agent.py
```

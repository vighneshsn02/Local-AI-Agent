"""
Interactive Rich Terminal CLI for the Local Coding AI Agent.
Features syntax highlighting, streaming tokens, tool inspection panels, and slash commands.
"""

import os
import sys
import argparse
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live
from rich.text import Text
from rich.prompt import Confirm
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

# Add parent directory to path to allow importing core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.agent import CodingAgent, AgentEvent


console = Console()


def print_banner(agent: CodingAgent):
    """Render welcome header banner."""
    status = agent.get_status()
    conn_str = "[bold green]Online (Ollama Connected)[/bold green]" if status["connected"] else "[bold red]Offline (Ollama Unreachable)[/bold red]"
    safe_str = "[bold yellow]ON[/bold yellow]" if status["safe_mode"] else "[bold green]OFF (Auto-execute)[/bold green]"

    banner_text = f"""[bold cyan]╔══════════════════════════════════════════════════════════════════╗
║              ⚡ LOCAL AI CODING AGENT (Ollama)                  ║
╚══════════════════════════════════════════════════════════════════╝[/bold cyan]
[bold white]Model:[/bold white] [bold magenta]{status['model']}[/bold magenta]  |  [bold white]Ollama:[/bold white] {conn_str}  |  [bold white]Safe Mode:[/bold white] {safe_str}
[bold white]Workspace:[/bold white] [blue]{status['workspace']}[/blue]
[dim]Type your coding task, or use [bold cyan]/help[/bold cyan] for slash commands. Press Ctrl+C to interrupt.[/dim]"""
    console.print(Panel(banner_text, border_style="cyan", padding=(1, 2)))


def print_help():
    """Print available slash commands."""
    table = Table(title="Available Slash Commands", border_style="cyan", show_lines=True)
    table.add_column("Command", style="bold cyan", width=20)
    table.add_column("Description", style="white")

    table.add_row("/model", "Select or switch the active local Ollama model")
    table.add_row("/models", "List all installed models in Ollama and their sizes")
    table.add_row("/safe", "Toggle safe confirmation mode for shell command execution")
    table.add_row("/files", "Show files and folders in current workspace")
    table.add_row("/read <path>", "Inspect and print the contents of a specific file")
    table.add_row("/clear", "Clear conversation history & reset memory")
    table.add_row("/status", "Display agent connection and configuration status")
    table.add_row("/help", "Show this help menu")
    table.add_row("/exit, quit", "Exit the coding agent CLI")

    console.print(table)


def handle_model_switch(agent: CodingAgent):
    """Interactive model selector."""
    models = agent.llm.list_models()
    if not models:
        console.print("[bold red]No local models found in Ollama or Ollama is offline.[/bold red]")
        return

    table = Table(title="Installed Local Ollama Models", border_style="magenta")
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("Model Name", style="bold white", width=30)
    table.add_column("Size", style="green", width=12)
    table.add_column("Active", style="cyan", width=8)

    for idx, m in enumerate(models, start=1):
        is_active = "👉 YES" if m["name"] == agent.llm.model else ""
        table.add_row(str(idx), m["name"], m["size"], is_active)

    console.print(table)

    choice = console.input("[bold cyan]Enter model number or name to switch (or press Enter to cancel): [/bold cyan]").strip()
    if not choice:
        return

    if choice.isdigit() and 1 <= int(choice) <= len(models):
        selected_model = models[int(choice) - 1]["name"]
    else:
        selected_model = choice

    agent.set_model(selected_model)
    console.print(f"[bold green]✔ Switched active model to:[/bold green] [bold magenta]{selected_model}[/bold magenta]\n")


def confirm_tool_execution(tool_name: str, args: dict) -> bool:
    """Prompt user for confirmation before executing a potentially destructive tool."""
    console.print(f"\n[bold yellow]⚠️ Safe Mode Confirmation Requested:[/bold yellow]")
    console.print(f"Tool: [bold cyan]{tool_name}[/bold cyan]")
    for k, v in args.items():
        console.print(f"  [dim]{k}:[/dim] {v}")
    return Confirm.ask("[bold yellow]Allow agent to execute this action?[/bold yellow]", default=True)


def run_interactive_cli(workspace: Optional[str] = None, model: str = "qwen2.5-coder:7b", safe: bool = False):
    """Main interactive REPL loop."""
    agent = CodingAgent(workspace_dir=workspace, model_name=model, safe_mode=safe)
    print_banner(agent)

    session = PromptSession(history=InMemoryHistory(), auto_suggest=AutoSuggestFromHistory())

    while True:
        try:
            user_input = session.prompt(
                f"\n👤 [{agent.llm.model}] >>> "
            ).strip()

            if not user_input:
                continue

            # Check for slash commands
            if user_input.startswith("/"):
                cmd_parts = user_input.split(maxsplit=1)
                cmd = cmd_parts[0].lower()
                arg = cmd_parts[1] if len(cmd_parts) > 1 else ""

                if cmd in ("/exit", "/quit"):
                    console.print("[bold yellow]Goodbye![/bold yellow]")
                    break
                elif cmd == "/help":
                    print_help()
                elif cmd == "/model":
                    handle_model_switch(agent)
                elif cmd == "/models":
                    models = agent.llm.list_models()
                    table = Table(title="Installed Models", border_style="cyan")
                    table.add_column("Model Name", style="bold white")
                    table.add_column("Size", style="green")
                    for m in models:
                        table.add_row(m["name"], m["size"])
                    console.print(table)
                elif cmd == "/safe":
                    agent.safe_mode = not agent.safe_mode
                    status_text = "[bold yellow]ENABLED[/bold yellow]" if agent.safe_mode else "[bold green]DISABLED[/bold green]"
                    console.print(f"Safe mode confirmation is now {status_text}")
                elif cmd == "/files":
                    res = agent.tools.list_directory(".")
                    console.print(Panel(res.output, title="Workspace Files", border_style="blue"))
                elif cmd == "/read":
                    if not arg:
                        console.print("[red]Usage: /read <file_path>[/red]")
                    else:
                        res = agent.tools.read_file(arg)
                        console.print(Panel(res.output, title=f"File: {arg}", border_style="blue"))
                elif cmd == "/clear":
                    agent.memory.clear()
                    console.print("[bold green]✔ Conversation memory cleared.[/bold green]")
                elif cmd == "/status":
                    status = agent.get_status()
                    console.print(Panel(
                        f"Model: {status['model']}\nWorkspace: {status['workspace']}\nConnected: {status['connected']}\nSafe Mode: {status['safe_mode']}\nHistory Turns: {status['history_turns']}",
                        title="Agent Status",
                        border_style="magenta"
                    ))
                else:
                    console.print(f"[bold red]Unknown command:[/bold red] {cmd}. Type [bold cyan]/help[/bold cyan] for available commands.")
                continue

            if user_input.lower() in ("exit", "quit"):
                console.print("[bold yellow]Goodbye![/bold yellow]")
                break

            # Execute user prompt through agent
            console.print(f"\n[bold magenta]🤖 Agent Reasoning...[/bold magenta]")

            accumulated_response = ""
            current_tool_box = None

            for event in agent.run_stream(user_input, confirm_callback=confirm_tool_execution):
                if event.type == "start":
                    pass
                elif event.type == "token":
                    delta = event.data.get("delta", "")
                    accumulated_response += delta
                elif event.type == "tool_start":
                    tool_name = event.data.get("tool", "")
                    tool_args = event.data.get("args", {})
                    step = event.data.get("step", 1)
                    args_summary = ", ".join(f"{k}={json.dumps(v)[:40]}" for k, v in tool_args.items())
                    console.print(f"[bold cyan]⚙ Step {step} ─ Calling tool:[/bold cyan] [bold yellow]{tool_name}[/bold yellow]({args_summary})")
                elif event.type == "tool_end":
                    tool_name = event.data.get("tool", "")
                    success = event.data.get("success", False)
                    output = event.data.get("output", "")
                    status_icon = "[bold green]✔ SUCCESS[/bold green]" if success else "[bold red]✖ FAILED[/bold red]"

                    # Truncate long tool outputs for console readability
                    display_output = output[:600] + ("\n... [output truncated]" if len(output) > 600 else "")
                    console.print(Panel(
                        display_output,
                        title=f"{status_icon} ─ {tool_name}",
                        border_style="green" if success else "red",
                        padding=(0, 1)
                    ))
                elif event.type == "message":
                    final_content = event.data.get("content", "")
                    console.print("\n" + "─" * 60)
                    console.print(Markdown(final_content))
                    console.print("─" * 60 + "\n")
                elif event.type == "error":
                    console.print(f"[bold red]❌ Error:[/bold red] {event.data.get('message')}")
                elif event.type == "done":
                    pass

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user.[/yellow]")
            continue
        except Exception as e:
            console.print(f"\n[bold red]Unhandled Exception:[/bold red] {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Local Autonomous Coding AI Agent CLI")
    parser.add_argument("--model", "-m", default="qwen2.5-coder:7b", help="Local Ollama model name (default: qwen2.5-coder:7b)")
    parser.add_argument("--workspace", "-w", default=".", help="Target workspace path (default: current directory)")
    parser.add_argument("--safe", "-s", action="store_true", help="Enable safe confirmation mode for commands")

    args = parser.parse_args()
    run_interactive_cli(workspace=args.workspace, model=args.model, safe=args.safe)


if __name__ == "__main__":
    main()

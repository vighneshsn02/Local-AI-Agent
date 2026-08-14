"""
Local Autonomous Coding AI Agent.
Unified entry point for both Interactive Terminal CLI and Modern Web UI.
"""

import sys
import argparse
from cli.main import run_interactive_cli
from web.app import start_server


def main():
    parser = argparse.ArgumentParser(
        description="Local Autonomous Coding AI Agent powered by Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py cli                    # Launch interactive Rich Terminal CLI
  python main.py cli --model llama3.2:3b # Launch CLI with specific model
  python main.py web                    # Launch Modern Web UI at http://127.0.0.1:5050
  python main.py web --port 8080        # Launch Web UI on custom port
        """
    )
    
    subparsers = parser.add_subparsers(dest="mode", help="Interface mode to launch (cli or web)")

    # CLI subparser
    cli_parser = subparsers.add_parser("cli", help="Start Interactive Terminal CLI")
    cli_parser.add_argument("--model", "-m", default="qwen2.5-coder:7b", help="Local Ollama model name (default: qwen2.5-coder:7b)")
    cli_parser.add_argument("--workspace", "-w", default=".", help="Target workspace path (default: current directory)")
    cli_parser.add_argument("--safe", "-s", action="store_true", help="Enable safe confirmation mode for commands")

    # Web subparser
    web_parser = subparsers.add_parser("web", help="Start Modern Web UI")
    web_parser.add_argument("--port", "-p", type=int, default=5050, help="Port to run Web UI on (default: 5050)")
    web_parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")

    args = parser.parse_args()

    # Default to CLI if no subcommand given
    if not args.mode or args.mode == "cli":
        model = getattr(args, "model", "qwen2.5-coder:7b")
        workspace = getattr(args, "workspace", ".")
        safe = getattr(args, "safe", False)
        run_interactive_cli(workspace=workspace, model=model, safe=safe)
    elif args.mode == "web":
        start_server(port=args.port, host=args.host)


if __name__ == "__main__":
    main()

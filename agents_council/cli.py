"""CLI for testing agents council without MCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agents import AgentExecutor, AgentRegistry, CouncilConvenor
from .models import AgentInvocation


def main() -> int:
    """CLI entry point for testing."""
    parser = argparse.ArgumentParser(description="Agents Council CLI")
    parser.add_argument(
        "--modes",
        type=Path,
        default=Path("modes.json"),
        help="Path to modes.json file",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    subparsers.add_parser("list", help="List all available agents")

    # Invoke command
    invoke_parser = subparsers.add_parser("invoke", help="Invoke a specific agent")
    invoke_parser.add_argument("agent_id", help="Agent mode ID")
    invoke_parser.add_argument("request", help="User request")
    invoke_parser.add_argument("--context", type=json.loads, default={}, help="Context JSON")

    # Council command
    council_parser = subparsers.add_parser("council", help="Prepare council dispatch")
    council_parser.add_argument("request", help="User request")
    council_parser.add_argument("--context", type=json.loads, default={}, help="Context JSON")

    args = parser.parse_args()

    try:
        registry = AgentRegistry(args.modes)
        executor = AgentExecutor(registry)
        convenor = CouncilConvenor(registry, executor)

        if args.command == "list":
            modes = registry.list_modes()
            print(json.dumps(modes, indent=2))

        elif args.command == "invoke":
            mode = registry.get_mode(args.agent_id)
            if not mode:
                print(f"Error: Agent '{args.agent_id}' not found.", file=sys.stderr)
                return 1

            invocation = AgentInvocation(
                mode_id=args.agent_id,
                user_request=args.request,
                context=args.context,
            )

            prompt = executor.build_prompt(mode, invocation)
            print("=" * 60)
            print(f"AGENT: {mode.name}")
            print("=" * 60)
            print(prompt)
            print("=" * 60)

        elif args.command == "council":
            dispatches = convenor.prepare_dispatch(args.request, args.context)
            print(json.dumps(dispatches, indent=2))

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

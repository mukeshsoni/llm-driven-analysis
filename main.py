#!/usr/bin/env python
"""
Main entry point for the LLM Query Processor application.
Can run in either API server mode or terminal chat mode.
"""

import sys
import asyncio
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="LLM Query Processor - Run as API server or terminal chat"
    )
    parser.add_argument(
        "--mode",
        choices=["api", "terminal"],
        default="api",
        help="Run mode: 'api' for REST API server, 'terminal' for interactive chat (default: api)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8003,
        help="Port for API server (only used in API mode, default: 8003)"
    )

    args = parser.parse_args()

    if args.mode == "api":
        print(f"Starting API server on port {args.port}...")
        from api_server import main as api_main
        asyncio.run(api_main())
    else:  # terminal mode
        from terminal_app import main as terminal_main
        asyncio.run(terminal_main())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python
"""
Main entry point for the LLM Query Processor application.
Can run in either API server mode or terminal chat mode.
"""

import sys
import asyncio
import argparse
from logger_config import get_logger, log_exception

# Initialize logger for this module
logger = get_logger(__name__)


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
        logger.info(f"Starting API server on port {args.port}...")
        from api_server import main as api_main
        asyncio.run(api_main())
    else:  # terminal mode
        logger.info("Starting terminal chat mode...")
        from terminal_app import main as terminal_main
        asyncio.run(terminal_main())


if __name__ == "__main__":
    try:
        logger.info("Starting LLM Query Processor application")
        main()
    except KeyboardInterrupt:
        logger.info("Application shutdown by user")
        sys.exit(0)
    except Exception as e:
        log_exception(logger, e, "Fatal error in main application")
        sys.exit(1)

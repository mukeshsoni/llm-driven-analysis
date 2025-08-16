import asyncio
from llm_processor import LLMQueryProcessor
from logger_config import get_logger, log_exception

# Initialize logger for this module
logger = get_logger(__name__)


async def main():
    """Run the terminal chat application."""
    logger.info("Starting terminal chat application")
    print("=" * 60)
    print("LLM Query Processor - Terminal Chat Mode")
    print("=" * 60)
    print("\nInitializing LLM processor...")

    # Use the context manager to ensure proper initialization and cleanup
    try:
        async with LLMQueryProcessor() as processor:
            logger.info("LLM processor initialized successfully")
            print("Ready! Type 'exit', 'quit', or 'bye' to end the conversation.\n")
            print("-" * 60)
            await processor.chat_loop()
    except Exception as e:
        log_exception(logger, e, "Error in terminal chat session")
        print(f"\nError during chat session: {e}")
        raise

    logger.info("Chat session ended. Resources cleaned up.")
    print("\nChat session ended. Resources cleaned up.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Terminal app interrupted by user")
        print("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        log_exception(logger, e, "Fatal error in terminal app")
        print(f"\nError: {e}")

import asyncio
from dotenv import load_dotenv

from mcp_client import LLMQueryProcessor

load_dotenv()

async def main():
    async with LLMQueryProcessor() as llm_processor:
        await llm_processor.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())

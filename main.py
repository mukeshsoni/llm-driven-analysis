import asyncio
from dotenv import load_dotenv

from mcp_client import MCPClient

load_dotenv()
model_name = "gpt-5"

async def main():
    # We need to create mcp_client with this async context, i.e. the async context in which we run main function
    # For that to happen, we have to implement __aenter__ and __aexit__ methods in MCPClient class
    async with MCPClient() as mcp_client:
        await mcp_client.connect_to_servers()
        await mcp_client.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())

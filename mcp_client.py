import os
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Optional
from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletionMessageParam
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        api_key = os.getenv("OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_ENDPOINT")
        api_version = "2025-01-01-preview"

        if not azure_endpoint:
            raise ValueError("AZURE_ENDPOINT environment variable is required")
        llm_client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self.llm_client = llm_client
        self.model_name = 'gpt-5'

    async def connect_to_servers(self):
        server_script_path = "./mcp_server.py"

        command = "python"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        # What does the enter_async_context do?
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("Connected to server with tools: ", [tool.name for tool in tools])

    async def process_query(self, conversations: list[ChatCompletionMessageParam]):
        # do something
        response = await self.llm_client.chat.completions.create(
            messages=conversations,
            max_completion_tokens=12000,
            temperature=1.0,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            model=self.model_name
        )
        return response.choices[0]

    async def chat_loop(self):
        conversations: list[ChatCompletionMessageParam] = [
            { "role": "system", "content": "You are a helpful assistant" }
        ]
        while True:
            user_input = input("User: ")
            conversations.append({
                "role": "user",
                "content": user_input
            })
            response = await self.process_query(conversations)
            print("\n")
            pprint(response.message.content)
            print("\n")

    async def cleanup(self):
        """Clean up resources"""
        if self.exit_stack:
            await self.exit_stack.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

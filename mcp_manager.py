from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Optional, List
from openai.types.chat import (
    ChatCompletionToolParam,
)
from openai.types.shared_params.function_definition import FunctionDefinition

class MCPManager:
    """Manages MCP server connections and tool operations."""

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[ChatCompletionToolParam] = []
        self.stdio = None
        self.write = None

    async def connect_to_servers(self):
        """Connect to MCP servers and initialize the session."""
        server_script_path = "./mcp_server_sql.py"

        command = "python"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        # stdio_client is the main guy. That function is what is creating a client which is connected to the mcp server.
        # It actually starts the mcp server and then maintains a connection with the server.
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        # What does the enter_async_context do?
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        self.available_tools = [
            ChatCompletionToolParam(
                type="function",
                function=FunctionDefinition(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.inputSchema
                )
            )
            for tool in tools
        ]
        print("Connected to server with tools: ", [tool.name for tool in tools])

    async def call_tool(self, tool_name: str, tool_args: dict):
        """Call a specific tool with the given arguments."""
        if self.session is None:
            raise RuntimeError("MCP session not initialized. Call connect_to_servers() first.")

        print(f"Calling tool: {tool_name}")
        print(f"Tool arguments: {tool_args}")

        tool_response = await self.session.call_tool(tool_name, tool_args)
        print(f"Got tool response for tool: {tool_name}")

        return tool_response

    def get_available_tools(self) -> List[ChatCompletionToolParam]:
        """Get the list of available tools."""
        return self.available_tools

    async def cleanup(self):
        """Clean up resources."""
        if self.exit_stack:
            await self.exit_stack.aclose()

    async def __aenter__(self):
        await self.connect_to_servers()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

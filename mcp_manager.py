from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Optional, List, Dict, Any
from openai.types.chat import (
    ChatCompletionToolParam,
)
from openai.types.shared_params.function_definition import FunctionDefinition

class ServerConfig:
    def __init__(self, command: str, args: List[str], env: Optional[dict[str, str]] = None):
        self.command = command
        self.args = args
        self.env = env

class MCPManager:
    """Manages MCP server connections and tool operations."""

    def __init__(self, server_configs):
        self.server_configs = {}
        for server_name, server_info in server_configs["mcpServers"].items():
            self.server_configs[server_name] = ServerConfig(server_info["command"], server_info.get("args", []))

        self.client: Optional[ClientSession] = None
        self.clients: dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[ChatCompletionToolParam] = []
        self.tool_to_server = {}
        self.stdio = None
        self.write = None

    async def connect_to_servers(self):
        """Connect to MCP servers and initialize the session."""
        print("Connecting to MCP servers...")
        for server_name, config in self.server_configs.items():
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env
            )

            try:
                # stdio_client is the main guy. That function is what is creating a client which is connected to the mcp server.
                # It actually starts the mcp server and then maintains a connection with the server.
                stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                self.stdio, self.write = stdio_transport
                # What does the enter_async_context do?
                client = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
                await client.initialize()
                self.clients[server_name] = client
                print(f"Connected to {server_name} MCP server")
            except Exception as e:
                print(f"Failed to connect to {server_name}: {e}")
        try:
            # TODO: Should we call load_tools somewhere else? From the creator or MCPManager instance?
            await self.load_tools()
        except Exception as e:
            print(f"Failed to load tools: {e}")

    async def load_tools(self):
        for server_name, client in self.clients.items():
            try:
                # List available tools for a server
                response = await client.list_tools()
                tools = response.tools
                for tool in tools:
                    # TODO: What happens if 2 MCP servers have the same tool name?
                    self.tool_to_server[tool.name] = server_name
                    self.available_tools.append(
                        ChatCompletionToolParam(
                            type="function",
                            function=FunctionDefinition(
                                name=tool.name,
                                description=tool.description,
                                parameters=tool.inputSchema
                            )
                        )
                    )
                    print(f"Loaded tool {tool.name} from {server_name}")
            except Exception as e:
                print(f"Failed to load tools for {server_name}: {e}")

    async def get_resource(self, server_name: str, uri: str) -> Optional[str]:
        """
        Fetch a specific resource from an MCP server.

        Args:
            server_name: Name of the MCP server
            uri: Resource URI

        Returns:
            Resource content as string, or None if not found
        """
        client = self.clients.get(server_name)
        if client is None:
            print(f"Server {server_name} not found")
            return None

        try:
            response = await client.read_resource(uri)
            if response.contents and len(response.contents) > 0:
                # Assuming text content for now
                content = response.contents[0]
                if hasattr(content, 'text'):
                    return content.text
                return str(content)
        except Exception as e:
            print(f"Failed to read resource {uri} from {server_name}: {e}")
            return None

    async def call_tool(self, tool_name: str, tool_args: dict):
        """Call a specific tool with the given arguments."""
        print(f"Calling tool: {tool_name}")
        print(f"Tool arguments: {tool_args}")

        server_name = self.tool_to_server.get(tool_name)
        if server_name is None:
            raise ValueError(f"Tool {tool_name} not found")

        client = self.clients[server_name]
        if client is None:
            raise RuntimeError("MCP session not initialized. Call connect_to_servers() first.")

        tool_response = await client.call_tool(tool_name, tool_args)
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

from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Optional, List, Dict, Any
import time
from openai.types.chat import (
    ChatCompletionToolParam,
)
from openai.types.shared_params.function_definition import FunctionDefinition
from logger_config import get_logger, log_exception

# Initialize logger for this module
logger = get_logger(__name__)

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
        logger.info("Connecting to MCP servers...")
        total_start = time.perf_counter()

        for server_name, config in self.server_configs.items():
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env
            )

            try:
                server_start = time.perf_counter()
                # stdio_client is the main guy. That function is what is creating a client which is connected to the mcp server.
                # It actually starts the mcp server and then maintains a connection with the server.
                stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                self.stdio, self.write = stdio_transport
                # What does the enter_async_context do?
                client = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
                await client.initialize()
                self.clients[server_name] = client
                server_time = time.perf_counter() - server_start
                logger.info(f"✅ Connected to MCP server '{server_name}' in {server_time:.3f}s")
            except Exception as e:
                log_exception(logger, e, f"Failed to connect to MCP server: {server_name}")
        try:
            # TODO: Should we call load_tools somewhere else? From the creator or MCPManager instance?
            await self.load_tools()
            total_time = time.perf_counter() - total_start
            logger.info(f"⏱️  Total MCP initialization time: {total_time:.3f}s")
        except Exception as e:
            log_exception(logger, e, "Failed to load tools")

    async def load_tools(self):
        """Load tools from all connected MCP servers."""
        logger.info("Loading tools from MCP servers...")
        load_start = time.perf_counter()
        total_tools = 0

        for server_name, client in self.clients.items():
            try:
                server_tool_start = time.perf_counter()
                # List available tools for a server
                response = await client.list_tools()
                tools = response.tools
                total_tools += len(tools)

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
                    logger.debug(f"Loaded tool '{tool.name}' from server '{server_name}'")

                server_tool_time = time.perf_counter() - server_tool_start
                logger.info(f"   └─ Loaded {len(tools)} tools from '{server_name}' in {server_tool_time:.3f}s")
            except Exception as e:
                log_exception(logger, e, f"Failed to load tools for server '{server_name}'")

        total_load_time = time.perf_counter() - load_start
        logger.info(f"📦 Loaded {total_tools} total tools in {total_load_time:.3f}s")

    async def get_resource(self, server_name: str, uri: str) -> Optional[str]:
        """
        Fetch a specific resource from an MCP server.

        Args:
            server_name: Name of the MCP server
            uri: Resource URI

        Returns:
            Resource content as string, or None if not found
        """
        # Print clients
        logger.info("MCPManager: get_resource")
        logger.info(self.clients)
        client = self.clients.get(server_name)
        if client is None:
            logger.error(f"Server '{server_name}' not found")
            return None

        try:
            logger.debug(f"Reading resource '{uri}' from server '{server_name}'")
            resource_start = time.perf_counter()
            response = await client.read_resource(uri)
            resource_time = time.perf_counter() - resource_start
            logger.debug(f"   └─ Resource read completed in {resource_time:.3f}s")

            if response.contents and len(response.contents) > 0:
                # Assuming text content for now
                content = response.contents[0]
                if hasattr(content, 'text'):
                    return content.text
                return str(content)
        except Exception as e:
            log_exception(logger, e, f"Failed to read resource '{uri}' from server '{server_name}'")
            return None

    async def call_tool(self, tool_name: str, tool_args: dict):
        """Call a specific tool with the given arguments."""
        tool_start = time.perf_counter()
        logger.info(f"🔧 Calling tool: {tool_name}")
        logger.debug(f"Tool arguments: {tool_args}")

        server_name = self.tool_to_server.get(tool_name)
        if server_name is None:
            logger.error(f"Tool '{tool_name}' not found in any connected server")
            raise ValueError(f"Tool {tool_name} not found")

        client = self.clients[server_name]
        if client is None:
            logger.error(f"Client for server '{server_name}' not initialized")
            raise RuntimeError("MCP session not initialized. Call connect_to_servers() first.")

        mcp_call_start = time.perf_counter()
        tool_response = await client.call_tool(tool_name, tool_args)
        mcp_call_time = time.perf_counter() - mcp_call_start

        total_tool_time = time.perf_counter() - tool_start
        logger.info(f"   ├─ MCP call time: {mcp_call_time:.3f}s")
        logger.info(f"   └─ Total tool time: {total_tool_time:.3f}s")
        logger.debug(f"Received response from tool '{tool_name}'")

        return tool_response

    def get_available_tools(self) -> List[ChatCompletionToolParam]:
        """Get the list of available tools."""
        return self.available_tools

    async def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up MCP manager resources...")
        if self.exit_stack:
            await self.exit_stack.aclose()
            logger.debug("Exit stack closed successfully")

    async def __aenter__(self):
        await self.connect_to_servers()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

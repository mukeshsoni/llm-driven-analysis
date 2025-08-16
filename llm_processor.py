from pydantic import BaseModel
import os
import asyncio
import time
from dotenv import load_dotenv
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionAssistantMessageParam,
)
import json
from openai import AsyncAzureOpenAI
from typing import Optional, List, Dict, Any
from mcp_manager import MCPManager
from logger_config import get_logger, log_exception

load_dotenv()

# Initialize logger for this module
logger = get_logger(__name__)

base_system_prompt = """
You are an AI assistant with access to multiple SQLite databases.
You have access to functions to query these databases:
- `list_databases`: To see all available databases
- `get_schema`: To get the schema of a specific database
- `run_query`: To run SQL queries against a specific database

Your goals are:
1. Interpret the user's request.
2. Identify which database to query (default to 'chinook' if not specified).
3. Write a correct and safe SQL query using the provided database schema.
4. Call the `run_query` function with the SQL and database name to get results.
5. After receiving the results, summarise them in natural language to directly answer the original question.

Guidelines:
- Always use the provided schema when forming SQL queries.
- Use SELECT statements only — never modify the database.
- Do not invent column or table names; stick to the schema.
- If the query involves conditions, be explicit in the WHERE clause.
- If the question is unclear or the database is ambiguous, ask clarifying questions.
- When querying, always specify the database parameter in run_query.

IMPORTANT: When responding to the user:
- Provide ONLY the final answer based on the query results
- Do NOT include your reasoning process, planning steps, or intermediate thoughts
- Do NOT show which tools you're calling or how you're constructing queries
- Do NOT include JSON objects or technical details about tool usage
- Simply present the information the user asked for in a clear, direct manner

"""

# Request and Response models
class LLMQueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class LLMQueryResponse(BaseModel):
    response: str
    session_id: str
    error: Optional[str] = None


class LLMQueryProcessor:
    """Processes LLM queries and orchestrates tool calls."""

    def __init__(self):
        self.model_name = 'gpt-5'
        self.mcp_manager: Optional[MCPManager] = None
        self.system_prompt = base_system_prompt

        # Initialize Azure OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_ENDPOINT")
        api_version = "2025-01-01-preview"

        if not azure_endpoint:
            logger.error("AZURE_ENDPOINT environment variable is not set")
            raise ValueError("AZURE_ENDPOINT environment variable is required")

        logger.info(f"Initializing LLM processor with model: {self.model_name}")
        self.llm_client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        logger.debug("Azure OpenAI client initialized successfully")

    async def initialize(self):
        """Initialize the MCP manager and connect to servers."""
        logger.info("Initializing MCP manager and connecting to servers...")
        server_configs = {
            "mcpServers": {
                # "filesystem": {
                #     "command": "python",
                #     "args": ["mcp_server_file_system.py"]
                # },
                "sql": {
                    "command": "python",
                    "args": ["mcp_server_sql.py"]
                }
            }
        }
        try:
            self.mcp_manager = MCPManager(server_configs)
            await self.mcp_manager.connect_to_servers()
            logger.info("Successfully connected to MCP servers")

            # Fetch database schema from MCP resource
            await self._load_database_schema()
        except Exception as e:
            log_exception(logger, e, "Failed to initialize MCP manager")
            raise

    async def _load_database_schema(self):
        """Load database schemas from MCP resources and update system prompt."""
        if not self.mcp_manager:
            logger.warning("MCP manager not initialized, skipping schema loading")
            return

        schemas_text = []

        # First, get the list of available databases
        try:
            logger.info("Fetching list of available databases...")
            databases_json = await self.mcp_manager.get_resource("sql", "databases://list")
            if databases_json:
                import json
                db_info = json.loads(databases_json)
                databases = db_info.get("databases", [])

                logger.info(f"Found {len(databases)} database(s)")

                # Fetch schema for each database
                for db in databases:
                    db_name = db['name']
                    schema_uri = db.get('schema_uri', f"schema://{db_name}")

                    logger.debug(f"Loading schema for {db_name} database...")
                    schema_content = await self.mcp_manager.get_resource("sql", schema_uri)

                    if schema_content:
                        schemas_text.append(f"\n## Database: {db_name}\n{db['description']}\n\n{schema_content}")
                        logger.info(f"Successfully loaded schema for {db_name}")
                    else:
                        logger.warning(f"Failed to load schema for {db_name}")

                if schemas_text:
                    self.system_prompt = base_system_prompt + "\n\nAvailable Databases and Schemas:\n" + "\n".join(schemas_text)
                    logger.info(f"Successfully loaded schemas for {len(schemas_text)} database(s)")
                else:
                    logger.warning("No schemas could be loaded from database list")
            else:
                logger.warning("Could not get list of databases from MCP resource")
        except Exception as e:
            log_exception(logger, e, "Error loading database list")

        # Fallback to single chinook database if list approach fails
        if not schemas_text:
            logger.info("Falling back to single database approach...")
            try:
                schema_content = await self.mcp_manager.get_resource("sql", "schema://chinook")
                if schema_content:
                    self.system_prompt = base_system_prompt + "\n\n## Database: chinook\nMusic store database\n\n" + schema_content
                    logger.info("Successfully loaded chinook database schema")
                else:
                    logger.warning("Using base system prompt without dynamic schema")
            except Exception as e:
                log_exception(logger, e, "Failed to load chinook database schema")

    async def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up LLM processor resources...")
        if self.mcp_manager:
            await self.mcp_manager.cleanup()
            logger.debug("MCP manager cleaned up successfully")

    async def call_llm(self, messages: list[ChatCompletionMessageParam]):
        """Make a call to the LLM with the given messages."""
        if not self.mcp_manager:
            logger.error("Attempted to call LLM without initialized MCP manager")
            raise RuntimeError("LLMQueryProcessor not initialized. Call initialize() first.")

        available_tools = self.mcp_manager.get_available_tools()
        logger.debug(f"Calling LLM with {len(messages)} messages and {len(available_tools)} available tools")

        try:
            llm_start = time.perf_counter()
            response = await self.llm_client.chat.completions.create(
                messages=messages,
                max_completion_tokens=12000,
                tools=available_tools,
                temperature=1.0,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                model=self.model_name
            )
            llm_time = time.perf_counter() - llm_start
            logger.info(f"🤖 LLM call completed in {llm_time:.3f}s (finish_reason: {response.choices[0].finish_reason})")
            return response.choices[0], llm_time
        except Exception as e:
            log_exception(logger, e, "Error calling LLM")
            raise

    async def process_query(self, query: str, conversation_history: Optional[List[ChatCompletionMessageParam]] = None):
        """Process a user query with optional conversation history."""
        if not self.mcp_manager:
            logger.error("Attempted to process query without initialized MCP manager")
            raise RuntimeError("LLMQueryProcessor not initialized. Call initialize() first.")

        logger.info(f"Processing query: {query[:100]}...")
        process_start = time.perf_counter()

        # Timing tracking
        timing_info = {
            'llm_time': 0.0,
            'llm_calls': 0,
            'tool_time': 0.0,
            'tool_calls': 0,
            'tool_details': []
        }

        # We don't allow LLM to go mad with tool calls. We clip it to 5 times.
        # E.g. It says "call tool 1 and 3", we do it, then it says "Now call tool 5 and 2" and so on
        # Each turn is counted as one. There can be any number of tool calls in each turn
        tool_call_turn = 0
        max_turns = 5
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
            logger.debug(f"Added {len(conversation_history)} messages from conversation history")

        messages.append({
            "role": "user",
            "content": query
        })

        response, llm_time = await self.call_llm(messages)
        timing_info['llm_time'] += llm_time
        timing_info['llm_calls'] += 1

        # If the response.choices[0].finish_reason is 'tool_calls', it means the LLM wants us to call a tool for it
        while tool_call_turn < max_turns and response.finish_reason == "tool_calls":
            tool_call_turn += 1
            logger.debug(f"Tool call turn {tool_call_turn}/{max_turns}")

            # We find the name of the tool it wants to call
            # Call the tool and get the tool response
            # Append the tool call response to the conversation
            tools = response.message.tool_calls
            if tools is not None:
                logger.info(f"🔧 LLM requested {len(tools)} tool call(s)")

                # We have to first append the message about tool call from LLM to conversations
                # With "role" as "assistant"
                messages.append(
                    ChatCompletionAssistantMessageParam(
                        role="assistant",
                        tool_calls=tools
                    )
                )

                for tool in tools:
                    if tool.type == 'function':
                        tool_name = tool.function.name
                        # The tool arguments are sent as a JSON string. We have to convert it to a python dictionary.
                        tool_args = json.loads(tool.function.arguments)
                        logger.debug(f"Calling tool: {tool_name} with args: {tool_args}")

                        try:
                            # Call tool using MCP manager
                            tool_start = time.perf_counter()
                            tool_response = await self.mcp_manager.call_tool(tool_name, tool_args)
                            tool_duration = time.perf_counter() - tool_start

                            timing_info['tool_time'] += tool_duration
                            timing_info['tool_calls'] += 1
                            timing_info['tool_details'].append({
                                'name': tool_name,
                                'duration': tool_duration
                            })

                            logger.info(f"   └─ Tool '{tool_name}' completed in {tool_duration:.3f}s")

                            # Enhance conversation with tool call response
                            # TODO: the response of the tool call is of type list[ContentBlock] and ContentBlock type is
                            # ContentBlock = TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource
                            # We need to either assert the type we are expecting from our MCP servers
                            # Or somehow handle the response of the response types
                            messages.append({
                                "role": "tool",
                                # Question: why are we passing a property called "tool_name" and passing it the response texts?
                                "content": json.dumps({
                                    **tool_args,
                                    "tool_name": [res.text for res in tool_response.content]
                                }),
                                "tool_call_id": tool.id
                            })
                        except Exception as e:
                            log_exception(logger, e, f"Error calling tool {tool_name}")
                            # Add error message to conversation
                            messages.append({
                                "role": "tool",
                                "content": json.dumps({
                                    "error": f"Tool call failed: {str(e)}"
                                }),
                                "tool_call_id": tool.id
                            })
                    else:
                        # TODO: Should we raise an exception here?
                        logger.warning(f"The LLM wanted to call a tool whose type was not function: {tool.type}. We only support function tools.")

                response, llm_time = await self.call_llm(messages)
                timing_info['llm_time'] += llm_time
                timing_info['llm_calls'] += 1
            else:
                break

        # Log processing summary
        total_process_time = time.perf_counter() - process_start
        logger.info(f"📊 Query processing summary:")
        logger.info(f"   ├─ Total processing time: {total_process_time:.3f}s")
        logger.info(f"   ├─ LLM calls: {timing_info['llm_calls']} ({timing_info['llm_time']:.3f}s total)")
        logger.info(f"   ├─ Tool calls: {timing_info['tool_calls']} ({timing_info['tool_time']:.3f}s total)")
        logger.info(f"   └─ Tool turns: {tool_call_turn}")

        if timing_info['tool_details']:
            logger.debug("Tool execution details:")
            for tool_detail in timing_info['tool_details']:
                logger.debug(f"   - {tool_detail['name']}: {tool_detail['duration']:.3f}s")

        # Return response, updated messages, and timing info
        return response.message.content, messages, timing_info

    async def chat_loop(self):
        """Run an interactive chat loop."""
        logger.info("Starting interactive chat loop")
        conversation_history = []
        while True:
            user_input = input("User: ")
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("Goodbye!")
                logger.info("Chat loop terminated by user")
                break

            try:
                response, updated_messages, timing_info = await self.process_query(user_input, conversation_history)
                # Store conversation history (excluding system prompt)
                conversation_history = [
                    msg for msg in updated_messages
                    if msg.get("role") != "system"
                ]
                print("\n")
                print(response)
                print("\n")
            except Exception as e:
                log_exception(logger, e, "Error in chat loop")
                print(f"Error: {str(e)}")

    async def __aenter__(self):
        """Async context manager entry."""
        logger.debug("Entering LLMQueryProcessor context")
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        logger.debug("Exiting LLMQueryProcessor context")
        if exc_type:
            logger.error(f"Exception in context: {exc_type.__name__}: {exc_val}")
        await self.cleanup()

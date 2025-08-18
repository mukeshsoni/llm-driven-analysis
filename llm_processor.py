from pydantic import BaseModel
import os
import asyncio
from dotenv import load_dotenv
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionAssistantMessageParam,
)
import json
from openai import AsyncAzureOpenAI
from typing import Optional, List
from mcp_manager import MCPManager

load_dotenv()

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
5. After receiving the results, provide a structured JSON response.

Guidelines:
- Always use the provided schema when forming SQL queries.
- Use SELECT statements only — never modify the database.
- Do not invent column or table names; stick to the schema.
- If the query involves conditions, be explicit in the WHERE clause.
- If the question is unclear or the database is ambiguous, ask clarifying questions.
- When querying, always specify the database parameter in run_query.

RESPONSE FORMAT:
You MUST provide with ONLY a valid JSON object in this exact format:
{
    "response": "Your natural language answer to the users question goes here",
    "chart": null or {chart configuration object}
}

CHART CONFIGURATION:
When the query results would benefit from visualization (e.g. trends, comparisons, distributions), include a chart configuration.
Otherwise, set chart property to null.

Chart configuration structure when applicable:
{
    "type": "bar|line|pie|scatter|area",
    "title": "Chart title",
    "data": {
        "labels": ["Label1", "Label2"...],
        "datasets": [
            {
                "label": "Dataset name",
                "data": [value1, value2, value3...],
                "backgroundColor": "rgba(75, 192, 192, 0.6)",
                "borderColor": "rgba(75, 192, 192, 1)"
            }
        ]
    },
    "options": {
        "scales": {
            "x": {"title": {"display": true, "text": "X Axis label"}},
            "y": {"title": {"display": true, "text": "Y Axis label"}}
        }
    }
}

Chart type selection:
- bar: For comparing categories
- line: For trends over time or continuous data
- pie: For showing parts of a whole (percentages/proportions)
- scatter: For showing relationship between two variables
- area: For showing cumulative trends

IMPORTANT:
- Your whole response MUST be a valid JSON object
- Do not include any text before or after the JSON object
- Ensure all strings are properly formatted
- Use null for chart when no visualization is needed
"""

# Request and Response models
class LLMQueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class LLMQueryResponse(BaseModel):
    response: str
    session_id: str
    chart_data: Optional[dict] = None
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
            raise ValueError("AZURE_ENDPOINT environment variable is required")

        self.llm_client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    async def initialize(self):
        """Initialize the MCP manager and connect to servers."""
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
        self.mcp_manager = MCPManager(server_configs)
        await self.mcp_manager.connect_to_servers()

        # Fetch database schema from MCP resource
        await self._load_database_schema()

    async def _load_database_schema(self):
        """Load database schemas from MCP resources and update system prompt."""
        if not self.mcp_manager:
            return

        schemas_text = []

        # First, get the list of available databases
        try:
            databases_json = await self.mcp_manager.get_resource("sql", "databases://list")
            if databases_json:
                import json
                db_info = json.loads(databases_json)
                databases = db_info.get("databases", [])

                print(f"Found {len(databases)} database(s)")

                # Fetch schema for each database
                for db in databases:
                    db_name = db['name']
                    schema_uri = db.get('schema_uri', f"schema://{db_name}")

                    print(f"Loading schema for {db_name} database...")
                    schema_content = await self.mcp_manager.get_resource("sql", schema_uri)

                    if schema_content:
                        schemas_text.append(f"\n## Database: {db_name}\n{db['description']}\n\n{schema_content}")
                        print(f"  ✓ Loaded schema for {db_name}")
                    else:
                        print(f"  ✗ Failed to load schema for {db_name}")

                if schemas_text:
                    self.system_prompt = base_system_prompt + "\n\nAvailable Databases and Schemas:\n" + "\n".join(schemas_text)
                    print(f"Successfully loaded schemas for {len(schemas_text)} database(s)")
                else:
                    print("No schemas could be loaded")
            else:
                print("Could not get list of databases")
        except Exception as e:
            print(f"Error loading database list: {e}")

        # Fallback to single chinook database if list approach fails
        if not schemas_text:
            print("Falling back to single database approach...")
            schema_content = await self.mcp_manager.get_resource("sql", "schema://chinook")
            if schema_content:
                self.system_prompt = base_system_prompt + "\n\n## Database: chinook\nMusic store database\n\n" + schema_content
                print("Successfully loaded chinook database schema")
            else:
                print("Using base system prompt without dynamic schema")

    async def cleanup(self):
        """Clean up resources."""
        if self.mcp_manager:
            await self.mcp_manager.cleanup()

    async def call_llm(self, messages: list[ChatCompletionMessageParam]):
        """Make a call to the LLM with the given messages."""
        if not self.mcp_manager:
            raise RuntimeError("LLMQueryProcessor not initialized. Call initialize() first.")

        available_tools = self.mcp_manager.get_available_tools()

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
        return response.choices[0]

    async def process_query(self, query: str, conversation_history: Optional[List[ChatCompletionMessageParam]] = None):
        """Process a user query with optional conversation history."""
        if not self.mcp_manager:
            raise RuntimeError("LLMQueryProcessor not initialized. Call initialize() first.")

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

        messages.append({
            "role": "user",
            "content": query
        })

        response = await self.call_llm(messages)

        # If the response.choices[0].finish_reason is 'tool_calls', it means the LLM wants us to call a tool for it
        while tool_call_turn < max_turns and response.finish_reason == "tool_calls":
            tool_call_turn += 1
            # We find the name of the tool it wants to call
            # Call the tool and get the tool response
            # Append the tool call response to the conversation
            tools = response.message.tool_calls
            if tools is not None:
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

                        # Call tool using MCP manager
                        tool_response = await self.mcp_manager.call_tool(tool_name, tool_args)

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
                    else:
                        # TODO: Should we raise an exception here?
                        print("The LLM wanted to call a tool whose type was not function. We only support function tools.")

                response = await self.call_llm(messages)
            else:
                break

        response_text = ""
        chart_data = None

        # We have asked the LLM to return content as a json object - {"response": string; chart: null | object}
        try:
            # Decode json string into python object
            json_response = json.loads(response.message.content)
            response_text = json_response.get("response", "")
            chart_data = json_response.get("chart", None)
        except json.JSONDecodeError as e:
            print(f"Response is not valid JSON. Treating it as plain text: {str(e)}")
            response_text = response.message.content
            chart_data = None
        except Exception as e:
            # logger.error(f"Error decoding LLM response as json {str(e)}")
            print(f"Error decoding LLM response as json {str(e)}")
        # # Return both response and updated messages for storage
        # return response.message.content, messages
        return response_text, chart_data, messages

    async def chat_loop(self):
        """Run an interactive chat loop."""
        conversation_history = []
        while True:
            user_input = input("User: ")
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("Goodbye!")
                break
            response_text, chart_data, updated_messages = await self.process_query(user_input, conversation_history)
            # Store conversation history (excluding system prompt)
            conversation_history = [
                msg for msg in updated_messages
                if msg.get("role") != "system"
            ]
            print("\n")
            print(response_text)
            if chart_data:
                print("\n[Chart data available - would be rendered in a UI]")
                print(f"Chart type: {chart_data.get('type', 'unknown')}")
            print("\n")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

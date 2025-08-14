from fastapi import FastAPI, HTTPException
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
from contextlib import asynccontextmanager
import uuid


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
5. After receiving the results, summarise them in natural language to directly answer the original question.

Guidelines:
- Always use the provided schema when forming SQL queries.
- Use SELECT statements only — never modify the database.
- Do not invent column or table names; stick to the schema.
- If the query involves conditions, be explicit in the WHERE clause.
- If the question is unclear or the database is ambiguous, ask clarifying questions.
- When querying, always specify the database parameter in run_query.

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
                "filesystem": {
                    "command": "python",
                    "args": ["mcp_server_file_system.py"]
                },
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

        # Return both response and updated messages for storage
        return response.message.content, messages

    async def chat_loop(self):
        """Run an interactive chat loop."""
        conversation_history = []
        while True:
            user_input = input("User: ")
            response, updated_messages = await self.process_query(user_input, conversation_history)
            # Store conversation history (excluding system prompt)
            conversation_history = [
                msg for msg in updated_messages
                if msg.get("role") != "system"
            ]
            print("\n")
            print(response)
            print("\n")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.llm_processor = LLMQueryProcessor()
    await app.state.llm_processor.initialize()
    app.state.chat_sessions = {}  # Dict[str, List[ChatCompletionMessageParam]]
    yield
    # Shutdown
    await app.state.llm_processor.cleanup()

app = FastAPI(lifespan=lifespan)

@app.post("/chat", response_model=LLMQueryResponse)
async def process_llm_query(request: LLMQueryRequest):
    """Process a query using the LLM with conversation memory."""
    if not hasattr(app.state, 'llm_processor') or not app.state.llm_processor:
        raise HTTPException(status_code=500, detail="LLM processor not initialized")

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())

    # Retrieve conversation history
    conversation_history = app.state.chat_sessions.get(session_id, [])

    try:
        # Process query with history
        response, updated_messages = await app.state.llm_processor.process_query(
            request.query,
            conversation_history
        )

        # Store updated conversation (excluding system prompt)
        app.state.chat_sessions[session_id] = [
            msg for msg in updated_messages
            if msg.get("role") != "system"
        ]

        return LLMQueryResponse(response=response, session_id=session_id)
    except Exception as e:
        return LLMQueryResponse(
            response="",
            session_id=session_id,
            error=f"Error processing query: {str(e)}"
        )

@app.delete("/chat/{session_id}")
async def clear_session(session_id: str):
    """Clear a specific conversation session."""
    if session_id in app.state.chat_sessions:
        del app.state.chat_sessions[session_id]
        return {"message": "Session cleared"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/chat/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session."""
    if session_id in app.state.chat_sessions:
        return {"session_id": session_id, "history": app.state.chat_sessions[session_id]}
    raise HTTPException(status_code=404, detail="Session not found")
async def main():
    """Run the FastAPI app with uvicorn."""
    import uvicorn
    await uvicorn.Server(
        uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8003,
            log_level="info"
        )
    ).serve()


if __name__ == "__main__":
    asyncio.run(main())

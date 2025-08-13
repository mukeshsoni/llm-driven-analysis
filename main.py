import os
import asyncio
from dotenv import load_dotenv
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionAssistantMessageParam,
)
import json
from openai import AsyncAzureOpenAI
from typing import Optional
from mcp_manager import MCPManager


load_dotenv()

system_prompt = """
You are an AI assistant for a music store database called "Chikoon DB".
You have access to a function called `run_query` that runs SQL queries against the SQLite database.

Your goals are:
1. Interpret the user's request.
2. Write a correct and safe SQL query using the provided database schema.
3. Call the `run_query` function with the SQL to get results.
4. After receiving the results, summarise them in natural language to directly answer the original question.

Guidelines:
- Always use the provided schema when forming SQL queries.
- Use SELECT statements only — never modify the database.
- Do not invent column or table names; stick to the schema.
- If the query involves conditions, be explicit in the WHERE clause.
- If the question is unclear, ask clarifying questions before generating SQL.

Here is the database schema:
<schema>
Tables:
- Artist(ArtistId, Name)
- Album(AlbumId, Title, ArtistId)
- Track(TrackId, Name, AlbumId, GenreId, Composer, Milliseconds, Bytes, UnitPrice)
- Genre(GenreId, Name)
- Customer(CustomerId, FirstName, LastName, Email, Country)
- Invoice(InvoiceId, CustomerId, InvoiceDate, BillingCountry, Total)
- InvoiceItem(InvoiceItemId, InvoiceId, TrackId, UnitPrice, Quantity)
</schema>
"""
class LLMQueryProcessor:
    """Processes LLM queries and orchestrates tool calls."""

    def __init__(self):
        self.model_name = 'gpt-5'
        self.mcp_manager: Optional[MCPManager] = None

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
        self.mcp_manager = MCPManager()
        await self.mcp_manager.connect_to_servers()

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

    async def process_query(self, query: str):
        """Process a user query, making LLM calls and tool calls as needed."""
        if not self.mcp_manager:
            raise RuntimeError("LLMQueryProcessor not initialized. Call initialize() first.")

        # We don't allow LLM to go mad with tool calls. We clip it to 5 times.
        # E.g. It says "call tool 1 and 3", we do it, then it says "Now call tool 5 and 2" and so on
        # Each turn is counted as one. There can be any number of tool calls in each turn
        tool_call_turn = 0
        max_turns = 5
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt}
        ]
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

        return response.message.content

    async def chat_loop(self):
        """Run an interactive chat loop."""
        while True:
            user_input = input("User: ")
            response = await self.process_query(user_input)
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

async def main():
    async with LLMQueryProcessor() as llm_processor:
        await llm_processor.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())

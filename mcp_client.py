import os
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Optional
from openai import AsyncAzureOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageToolCallParam,
)
from openai.types.shared_params.function_definition import FunctionDefinition
from dotenv import load_dotenv
from pprint import pprint
import json

load_dotenv()

system_prompt = "You are a helpful assistant."
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

    async def process_query(self, messages: list[ChatCompletionMessageParam]):
        # do something
        response = await self.llm_client.chat.completions.create(
            messages=messages,
            max_completion_tokens=12000,
            tools=self.available_tools,
            temperature=1.0,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            model=self.model_name
        )
        return response.choices[0]

    async def chat_loop(self):
        messages: list[ChatCompletionMessageParam] = [
            { "role": "system", "content": system_prompt }
        ]
        while True:
            # We don't allow LLM to go mad with tool calls. We clip it to 5 times.
            # E.g. It says "call tool 1 and 3", we do it, then it says "Now call tool 5 and 2" and so on
            # Each turn is counted as one. There can be any number of tool calls in each turn
            tool_call_turn = 0
            max_turns = 5
            user_input = input("User: ")
            messages.append({
                "role": "user",
                "content": user_input
            })
            response = await self.process_query(messages)
            # If the response.choices[0].finish_reason is 'tool_calls', it means the LLM wants us to call a tool for it
            while tool_call_turn < max_turns and response.finish_reason == "tool_calls":
                tool_call_turn += 1
                # We find the name of the tool it wants to call
                # Call the tool and get the tool response
                # Append the tool call response to the conversation
                tools = response.message.tool_calls
                if tools != None and self.session != None:
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
                            print("Calling tool:", tool.function)
                            tool_name = tool.function.name
                            # The tool arguments are sent as a JSON string. We have to convert it to a python dictionary.
                            tool_args = json.loads(tool.function.arguments)
                            print("Tool name:", tool_name)
                            print("Tool arguments:", tool_args)
                            # Call tool and get tool response
                            tool_response = await self.session.call_tool(tool_name, tool_args)
                            print("Got tool response for tool: ", tool_name)
                            # Enhance conversation with tool call response
                            # TODO: the response of the tool call is of type list[ContentBlock] and ContentBlock type is
                            # ContentBlock = TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource
                            # We need to either assert the type we are expecting from our MCP servers
                            # Or somehow handle the respone of the response types
                            messages.append({
                                "role": "tool",
                                # Question: why are we passing a property called "tool_name" and passing it the response texts?
                                "content": json.dumps({ **tool_args, "tool_name": [res.text for res in tool_response.content] }),
                                "tool_call_id": tools[0].id
                            })
                        else:
                            # TODO: Should we raise an exception here?
                            print("The LLM wanted to call a tool whose type was not function. We only support function tools.")
                    response = await self.process_query(messages)
                else:
                    break
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

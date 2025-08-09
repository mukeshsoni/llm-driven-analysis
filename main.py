import asyncio
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam

from mcp_client import MCPClient

load_dotenv()
model_name = "gpt-5"

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_ENDPOINT")

    if not azure_endpoint:
        raise ValueError("AZURE_ENDPOINT environment variable is required")

    # We need to create mcp_client with this async context, i.e. the async context in which we run main function
    # For that to happen, we have to implement __aenter__ and __aexit__ methods in MCPClient class
    async with MCPClient() as mcp_client:
        await mcp_client.connect_to_servers()
    # client = AzureOpenAI(
    #     api_version="2025-01-01-preview",
    #     azure_endpoint=azure_endpoint,
    #     api_key=api_key
    # )
    # conversations: list[ChatCompletionMessageParam] = [
    #     {
    #         "role": "system",
    #         "content": "You are a helpful assistant."
    #     }
    # ]

    # while True:
    #     input_str = input("Query: ")
    #     conversations.append({"role": "user", "content": input_str})
    #     response = client.chat.completions.create(
    #         messages=conversations,
    #         max_completion_tokens=12000,
    #         temperature=1.0,
    #         top_p=1.0,
    #         frequency_penalty=0.0,
    #         presence_penalty=0.0,
    #         model=model_name
    #     )
    #     print(response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(main())

import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam

load_dotenv()
model_name = "gpt-5"

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_ENDPOINT")

    if not azure_endpoint:
        raise ValueError("AZURE_ENDPOINT environment variable is required")

    client = AzureOpenAI(
        api_version="2025-01-01-preview",
        azure_endpoint=azure_endpoint,
        api_key=api_key
    )
    conversations: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        }
    ]

    while True:
        input_str = input("Query: ")
        conversations.append({"role": "user", "content": input_str})
        response = client.chat.completions.create(
            messages=conversations,
            max_completion_tokens=12000,
            temperature=1.0,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            model=model_name
        )
        print(response.choices[0].message.content)

if __name__ == "__main__":
    main()

"""
Example usage of DeepAnalyze OpenAI-Compatible API with OpenAI library
Demonstrates assistant workflow with analyze tool
"""

import openai
import time
import re
from pathlib import Path

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.append(str(API_DIR))

from config import API_PUBLIC_BASE_V1, VLLM_BASE_URL_NO_V1, DEEPANALYZE_VLLM_API_KEY

# Configure OpenAI client for DeepAnalyze
API_BASE = API_PUBLIC_BASE_V1
MODEL = "DeepAnalyze-8B"

client = openai.OpenAI(
    base_url=API_BASE,
    api_key=DEEPANALYZE_VLLM_API_KEY
)

def file_api_examples():
    """Demonstrate various file API operations"""
    try:
        # Create test file
        test_file_path = Path("test.txt")
        test_file_path.write_text("Test content")

        # Create files with different purposes
        file1 = client.files.create(file=test_file_path, purpose="file-extract")
        file2 = client.files.create(file=test_file_path, purpose="file-extract")

        print(f"Created files: {file1.id} (extract), {file2.id} (assistants)")

        # List files
        files_list = client.files.list()
        print(f"Total files: {len(files_list.data)}")

        # Get content (file-extract purpose)
        if file1.purpose == "file-extract":
            content = client.files.content(file1.id)
            print(f"File content: {content.text}")

        # Cleanup
        client.files.delete(file1.id)
        client.files.delete(file2.id)
        test_file_path.unlink()
        print("✅ File API examples completed")

    except Exception as e:
        print(f"❌ Error: {e}")


def chat_completion_with_message_file_ids():
    """Chat completion with file_ids in messages (OpenAI compatibility)"""
    try:
        # Use existing Simpson.csv file
        with open("./Simpson.csv", "rb") as f:
            file_obj = client.files.create(file=f, purpose="file-extract")

        # New format: file_ids in messages
        messages = [
            {
                "role": "user",
                "content": "分析数据，总结主要发现。",
                "file_ids": [file_obj.id]
            }
        ]

        response = client.chat.completions.create(model=MODEL, messages=messages)
        message = response.choices[0].message

        print(f"Response: {message.content}")

        # Show files from both formats
        if hasattr(message, 'files') and message.files:
            print(f"Files (message): {len(message.files)}")
        if hasattr(response, 'generated_files') and response.generated_files:
            print(f"Files (response): {len(response.generated_files)}")
        for file in response.generated_files:
            print(f"- {file['name']}: {file['url']}")
        

    except Exception as e:
        print(f"❌ Error: {e}")


def streaming_chat_completion_with_files():
    """Streaming chat completion with file handling"""
    try:
        # Use existing Simpson.csv file
        with open("./Simpson.csv", "rb") as f:
            file_obj = client.files.create(file=f, purpose="file-extract")

        # Streaming with file_ids in messages
        messages = [
            {
                "role": "user",
                "content": "分析数据并生成可视化图表。",
                "file_ids": [file_obj.id]
            }
        ]

        print("Streaming...")
        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True
        )

        full_response = ""
        collected_files = []

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)
                full_response += content

            # Collect files from chunks
            if hasattr(chunk, 'generated_files') and chunk.generated_files:
                collected_files.extend(chunk.generated_files)



        print(f"\n✅ Streaming complete ({len(full_response)} chars, {len(collected_files)} files)")
        for file in collected_files:
            print(f"- {file['name']}: {file['url']}")


    except Exception as e:
        print(f"❌ Error: {e}")






def main():
    """Interactive example selector"""
    print("🚀 DeepAnalyze API Examples")
    print(f"API: {API_PUBLIC_BASE_V1} | Model: {VLLM_BASE_URL_NO_V1}\n")

    examples = {
        "1": ("File API", file_api_examples),
        "2": ("Chat Completion", chat_completion_with_message_file_ids),
        "3": ("Streaming", streaming_chat_completion_with_files),
        "4": ("All Examples", None)
    }

    while True:
        print("📋 Examples:")
        for num, (name, _) in examples.items():
            print(f"{num}. {name}")
        print("0. Exit")

        choice = input("\nSelect (0-4): ").strip()

        if choice == "0":
            print("👋 Goodbye!")
            break

        if choice not in examples:
            print("❌ Invalid choice")
            continue

        try:
            # Test connection
            models = client.models.list()
            print(f"✅ Connected: {[m.id for m in models.data]}")

            if choice == "4":  # Run all examples
                for num, (name, func) in list(examples.items())[:-1]:
                    print(f"\n{name}:")
                    func()
            else:
                name, func = examples[choice]
                print(f"\n{name}:")
                func()

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Ensure API server and model server are running (see API/config.py)")
            if choice in ["2", "4"]:
                print("And Simpson.csv exists in current directory")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Example usage of DeepAnalyze OpenAI-Compatible src/api
Demonstrates common use cases
"""

import requests
import time
import json

import sys
from pathlib import Path

src/api_DIR = Path(__file__).resolve().parents[1]
if str(src/api_DIR) not in sys.path:
    sys.path.append(str(src/api_DIR))

from config import src/api_PUBLIC_BASE, VLLM_BASE_URL_NO_V1

src/api_BASE = src/api_PUBLIC_BASE
MODEL = "default"


def simple_chat():
    """Simple chat without files"""
    response = requests.post(f"{src/api_BASE}/v1/chat/completions", json={
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "用一句话介绍Python编程语言"}
        ],
        "temporaryerature": 0.3
    })

    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"Assistant: {content[:100]}...")
    else:
        print(f"❌ Error: {response.text}")


def chat_with_file():
    """Chat with file attachment"""
    # Upload file
    with open("./Simpson.csv", 'rb') as f:
        files = {'file': ('Simpson.csv', f, 'text/csv')}
        data = {'purpose': 'file-extract'}
        response = requests.post(f"{src/api_BASE}/v1/files", files=files, data=data)

    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        return

    file_id = response.json()['id']

    # Chat with file
    response = requests.post(f"{src/api_BASE}/v1/chat/completions", json={
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "分析哪种教学方法效果更好。"}
        ],
        "file_ids": [file_id],
        "temporaryerature": 0.3
    })

    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"Response: {content}...")

        files = result.get('generated_files', [])
        if files:
            print(f"Files: {len(files)} generated")

    # Cleanup
    # requests.delete(f"{src/api_BASE}/v1/files/{file_id}")




def file_ids_in_messages():
    """Chat completion with file_ids in messages (OpenAI compatibility)"""
    # Upload file
    with open("./Simpson.csv", 'rb') as f:
        files = {'file': ('Simpson.csv', f, 'text/csv')}
        data = {'purpose': 'file-extract'}
        response = requests.post(f"{src/api_BASE}/v1/files", files=files, data=data)

    file_id = response.json()['id']

    # New format: file_ids in messages
    response = requests.post(f"{src/api_BASE}/v1/chat/completions", json={
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "分析数据并生成可视化图表。",
                "file_ids": [file_id]  # can both be inside message and top-level, for compatibility with OpenAI src/api
            }
        ],
        "temporaryerature": 0.3
    })

    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"Response: {content[:100]}...")

        # Check for files in message (new format)
        message = result['choices'][0]['message']
        if 'files' in message:
            print(f"Files in message: {len(message['files'])}")

        # Check for generated_files (backward compatibility)
        if 'generated_files' in result:
            print(f"Generated files: {len(result['generated_files'])}")

    # Cleanup
    # requests.delete(f"{src/api_BASE}/v1/files/{file_id}")


def streaming_chat():
    """Streaming chat response"""
    # Upload file
    with open("./Simpson.csv", 'rb') as f:
        files = {'file': ('Simpson.csv', f, 'text/csv')}
        data = {'purpose': 'file-extract'}
        response = requests.post(f"{src/api_BASE}/v1/files", files=files, data=data)

    file_id = response.json()['id']

    print("Streaming response...")
    response = requests.post(
        f"{src/api_BASE}/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": "分析数据并生成趋势图。",
                    "file_ids": [file_id]
                }
            ],
            "temporaryerature": 0.3,
            "stream": True
        },
        stream=True
    )

    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data_str)
                        if 'choices' in chunk and chunk['choices']:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                print(delta['content'], end='', flush=True)
                        if 'generated_files' in chunk:
                            print(f"\n\n📁 New file generated: {chunk['generated_files']}")
                    except json.JSONDecodeError:
                        pass
        print("\n✅ Streaming complete")

    


def check_server():
    """Check if src/api server is running"""
    try:
        response = requests.get(f"{src/api_BASE}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def main():
    """Run data/exampless"""
    print("🚀 DeepAnalyze src/api Examples")
    print(f"src/api: {src/api_PUBLIC_BASE} | Model: {VLLM_BASE_URL_NO_V1}")

    data/exampless = {
        "1": ("Simple Chat", simple_chat),
        "2": ("Chat with File", chat_with_file),
        "3": ("File IDs in Messages", file_ids_in_messages),
        "4": ("Streaming Chat", streaming_chat),
        "5": ("All Examples", None)
    }

    while True:
        print("\n📋 Examples:")
        for num, (name, _) in data/exampless.items():
            print(f"{num}. {name}")
        print("0. Exit")

        choice = input("\nSelect (0-5): ").strip()

        if choice == "0":
            print("👋 Goodbye!")
            break

        if choice not in data/exampless:
            print("❌ Invalid choice")
            continue

        try:
            if choice == "5":  # Run all data/exampless
                for num, (name, func) in list(data/exampless.items())[:-1]:
                    print(f"\n{name}:")
                    func()
            else:
                name, func = data/exampless[choice]
                print(f"\n{name}:")
                func()

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Ensure src/api server and model server are running (see src/api/config.py)")


if __name__ == "__main__":
    main()

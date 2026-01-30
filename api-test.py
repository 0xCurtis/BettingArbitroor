import requests

from config import OLLAMA_AUTH, OLLAMA_MODEL, OLLAMA_URL


def test_ollama_connection() -> None:
    chat_payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"},
        ],
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {OLLAMA_AUTH}"}
    chat_resp = requests.post(
        f"{OLLAMA_URL}/v1/generate", json=chat_payload, headers=headers, timeout=60
    )
    return chat_resp


print(test_ollama_connection())

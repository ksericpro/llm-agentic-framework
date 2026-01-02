import requests
import json

def test_api():
    url = "http://127.0.0.1:8000/api/query"
    payload = {
        "query": "What is the capital of France?",
        "session_id": "test_session_999",
        "stream": False
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()

import requests
import json

def test_guitar_gallery():
    url = "http://localhost:8000/api/query"
    payload = {
        "query": "Extract the contact information and location from https://www.guitargallery.com.sg/",
        "stream": False,
        "temperature": 0.1
    }
    
    print(f"Testing URL: {payload['query']}")
    print("Sending request...")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        print("\n" + "="*80)
        print("GUITAR GALLERY TEST RESULTS")
        print("="*80)
        print(f"Tool Used: {result.get('routing_decision')}")
        print(f"\nAnswer:\n{result.get('final_answer')}")
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_guitar_gallery()

import requests
import json
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

def test_guitar_gallery():
    url = "http://localhost:8000/api/stream"
    payload = {
        "query": "What acoustic guitars are currently featured on https://www.guitargallery.com.sg/ and what are their prices?",
        "stream": True,
        "temperature": 0.1
    }
    
    print(f"Testing URL: {payload['query']}")
    print("Sending request...")
    
    try:
        response = requests.post(url, json=payload, stream=True, timeout=60)
        response.raise_for_status()
        
        final_answer = ""
        routing_decision = ""
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                data = json.loads(line[6:])
                if 'node' in data:
                    node = data['node']
                    state = data.get('state', {})
                    if state.get('routing_decision'):
                        routing_decision = state['routing_decision']
                        print(f"📍 Node: {node}, Decision: {routing_decision}")
                    if state.get('final_answer'):
                        final_answer = state['final_answer']
                elif data.get('event') == 'complete':
                    print("\n✅ Final Answer Received:")
                    print("-" * 40)
                    print(final_answer)
                    print("-" * 40)
                    print(f"Tool Used: {routing_decision}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_guitar_gallery()

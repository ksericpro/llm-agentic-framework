"""
Example client code for testing the LangChain Agentic Pipeline API
Demonstrates both streaming and non-streaming requests
"""

import requests
import json
import sseclient  # pip install sseclient-py
from typing import Optional, List, Dict


class AgenticPipelineClient:
    """Client for interacting with the LangChain Agentic Pipeline API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> Dict:
        """Check API health status"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def query(
        self,
        query: str,
        chat_history: Optional[List[Dict]] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7
    ) -> Dict:
        """
        Send a non-streaming query to the pipeline
        
        Args:
            query: User's question
            chat_history: Previous conversation messages
            model: OpenAI model to use
            temperature: LLM temperature
        
        Returns:
            Dictionary with the final answer and metadata
        """
        payload = {
            "query": query,
            "chat_history": chat_history or [],
            "stream": False,
            "model": model,
            "temperature": temperature
        }
        
        response = self.session.post(
            f"{self.base_url}/api/query",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def stream_query(
        self,
        query: str,
        chat_history: Optional[List[Dict]] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7
    ):
        """
        Send a streaming query to the pipeline
        
        Args:
            query: User's question
            chat_history: Previous conversation messages
            model: OpenAI model to use
            temperature: LLM temperature
        
        Yields:
            Dictionary events as they arrive from the pipeline
        """
        payload = {
            "query": query,
            "chat_history": chat_history or [],
            "stream": True,
            "model": model,
            "temperature": temperature
        }
        
        response = self.session.post(
            f"{self.base_url}/api/stream",
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"}
        )
        response.raise_for_status()
        
        # Parse SSE events
        client = sseclient.SSEClient(response)
        for event in client.events():
            if event.data:
                try:
                    data = json.loads(event.data)
                    yield data
                except json.JSONDecodeError:
                    print(f"Failed to parse event: {event.data}")


# ============================================================================
# Example Usage
# ============================================================================

def example_non_streaming():
    """Example: Non-streaming query"""
    print("=" * 80)
    print("NON-STREAMING QUERY EXAMPLE")
    print("=" * 80)
    
    client = AgenticPipelineClient()
    
    # Check health
    print("\n1. Checking API health...")
    health = client.health_check()
    print(f"   Status: {health['status']}")
    print(f"   OpenAI configured: {health['openai_configured']}")
    print(f"   Tavily configured: {health['tavily_configured']}")
    
    # Send query
    print("\n2. Sending query...")
    query = "What are the latest developments in artificial intelligence?"
    
    result = client.query(query)
    
    print(f"\n3. Results:")
    print(f"   Success: {result['success']}")
    print(f"   Intent: {result.get('intent', 'N/A')}")
    print(f"   Routing: {result.get('routing_decision', 'N/A')}")
    print(f"\n   Answer:\n   {result['final_answer']}")
    
    if result.get('citations'):
        print(f"\n   Citations: {result['citations']}")


def example_streaming():
    """Example: Streaming query"""
    print("\n" + "=" * 80)
    print("STREAMING QUERY EXAMPLE")
    print("=" * 80)
    
    client = AgenticPipelineClient()
    
    query = "Explain quantum computing in simple terms"
    
    print(f"\nQuery: {query}")
    print("\nStreaming response:\n")
    
    for event in client.stream_query(query):
        event_type = event.get('event')
        
        if event_type == 'start':
            print(f"🚀 Pipeline started for: {event['query']}")
        
        elif event_type == 'complete':
            print("\n✅ Pipeline complete!")
        
        elif event_type == 'error':
            print(f"\n❌ Error: {event['error']}")
        
        else:
            # Node event
            node = event.get('node', 'unknown')
            state = event.get('state', {})
            
            print(f"\n📍 Node: {node}")
            
            if state.get('routing_decision'):
                print(f"   Routing: {state['routing_decision']}")
            
            if state.get('intent'):
                print(f"   Intent: {state['intent']}")
            
            if state.get('draft_answer'):
                print(f"   Draft: {state['draft_answer'][:100]}...")
            
            if state.get('final_answer'):
                print(f"\n   Final Answer:\n   {state['final_answer']}")


def example_with_chat_history():
    """Example: Query with chat history"""
    print("\n" + "=" * 80)
    print("CHAT HISTORY EXAMPLE")
    print("=" * 80)
    
    client = AgenticPipelineClient()
    
    # Simulate a conversation
    chat_history = [
        {"role": "user", "content": "What is machine learning?"},
        {"role": "assistant", "content": "Machine learning is a subset of AI..."}
    ]
    
    query = "Can you give me an example?"
    
    print(f"\nPrevious conversation:")
    for msg in chat_history:
        print(f"  {msg['role']}: {msg['content'][:50]}...")
    
    print(f"\nNew query: {query}")
    
    result = client.query(query, chat_history=chat_history)
    
    print(f"\nAnswer:\n{result['final_answer']}")


def example_error_handling():
    """Example: Error handling"""
    print("\n" + "=" * 80)
    print("ERROR HANDLING EXAMPLE")
    print("=" * 80)
    
    client = AgenticPipelineClient()
    
    try:
        # Try with empty query (should fail validation)
        result = client.query("")
    except requests.exceptions.HTTPError as e:
        print(f"\n✅ Caught expected error: {e}")
        print(f"   Response: {e.response.json()}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("LANGCHAIN AGENTIC PIPELINE - CLIENT EXAMPLES")
    print("=" * 80)
    
    try:
        # Run examples
        example_non_streaming()
        example_streaming()
        example_with_chat_history()
        example_error_handling()
        
        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETED!")
        print("=" * 80 + "\n")
    
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API")
        print("   Make sure the API is running: python api.py")
        print("   Or: uvicorn api:app --reload --port 8000\n")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")

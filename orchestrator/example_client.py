"""
Example client code for testing the LangChain Agentic Pipeline API
Demonstrates both streaming and non-streaming requests
"""

import requests
import json
from typing import Optional, List, Dict


class AgenticPipelineClient:
    """Client for interacting with the LangChain Agentic Pipeline API"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
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
        
        # Parse SSE events manually
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                data_str = line[6:]  # Remove 'data: ' prefix
                try:
                    data = json.loads(data_str)
                    yield data
                except json.JSONDecodeError:
                    print(f"Failed to parse event: {data_str}")


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
    
    print("\n3. Results:")
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
    
    print("\nPrevious conversation:")
    for msg in chat_history:
        print(f"  {msg['role']}: {msg['content'][:50]}...")
    
    print(f"\nNew query: {query}")
    
    result = client.query(query, chat_history=chat_history)
    
    print(f"\nAnswer:\n{result['final_answer']}")


def example_rich_dad_poor_dad_questions():
    """Example: Ask questions about Rich Dad Poor Dad book"""
    print("\n" + "=" * 80)
    print("RICH DAD POOR DAD - KNOWLEDGE BASE QUERIES")
    print("=" * 80)
    
    client = AgenticPipelineClient()
    
    # Sample questions about the book
    questions = [
        "What are the main lessons from Rich Dad Poor Dad?",
        "What is the difference between assets and liabilities according to Rich Dad Poor Dad?",
        "What does Robert Kiyosaki say about financial education?",
        "What are the key differences between how rich dad and poor dad think about money?",
        "What is the cash flow quadrant mentioned in the book?"
    ]
    
    print("\nAsking questions about Rich Dad Poor Dad...\n")
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'─' * 80}")
        print(f"Question {i}: {question}")
        print('─' * 80)
        
        try:
            result = client.query(question, temperature=0.3)
            
            if result['success']:
                print(f"\n✅ Answer:\n{result['final_answer']}\n")
                
                if result.get('citations'):
                    print(f"📚 Sources: {len(result['citations'])} citations")
                
                if result.get('routing_decision'):
                    print(f"🔀 Routing: {result['routing_decision']}")
            else:
                print(f"\n❌ Query failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
        
        # Add a small delay between questions to avoid overwhelming the API
        if i < len(questions):
            import time
            time.sleep(1)
    
    print("\n" + "=" * 80)
    print("RICH DAD POOR DAD QUERIES COMPLETED")
    print("=" * 80)


def example_rich_dad_streaming():
    """Example: Streaming query about Rich Dad Poor Dad"""
    print("\n" + "=" * 80)
    print("RICH DAD POOR DAD - STREAMING QUERY (RAG TEST)")
    print("=" * 80)
    
    client = AgenticPipelineClient()
    
    query = "What are the most important lessons written in Rich Dad Poor Dad?"
    
    print(f"\nQuery: {query}")
    print("\nStreaming response:\n")
    
    routing_used = None
    
    for event in client.stream_query(query, temperature=0.3):
        event_type = event.get('event')
        
        if event_type == 'start':
            print("🚀 Pipeline started")
        
        elif event_type == 'complete':
            print("\n✅ Pipeline complete!")
            
            # Summary of routing
            if routing_used:
                print(f"\n{'='*80}")
                print("ROUTING SUMMARY:")
                print(f"{'='*80}")
                if "internal_retrieval" in routing_used.lower():
                    print(f"✅ RAG WAS USED! Tool: {routing_used}")
                    print("   This means the answer came from your PDF knowledge base!")
                else:
                    print(f"⚠️  RAG NOT USED. Tool: {routing_used}")
                    print(f"   The answer came from: {routing_used}")
                print(f"{'='*80}")
        
        elif event_type == 'error':
            print(f"\n❌ Error: {event['error']}")
        
        else:
            # Node event
            node = event.get('node', 'unknown')
            state = event.get('state', {})
            
            print(f"\n📍 Node: {node}")
            
            if state.get('routing_decision') and state['routing_decision'] not in ['None', None]:
                routing_str = state['routing_decision']
                routing_used = routing_str
                print(f"   🔀 Routing: {routing_str}")
                
                # Parse and highlight if RAG is used
                if "internal_retrieval" in routing_str.lower():
                    print("   ✅ RAG/Internal Retrieval ACTIVATED!")
                elif "web_search" in routing_str.lower():
                    print("   🌐 Web Search activated (not using RAG)")
                elif "calculator" in routing_str.lower():
                    print("   🔢 Calculator activated (not using RAG)")
            
            if state.get('intent'):
                print(f"   🎯 Intent: {state['intent']}")
            
            if state.get('retrieved_docs'):
                print(f"   📚 Retrieved: {len(state['retrieved_docs'])} documents from knowledge base")
            
            if state.get('final_answer'):
                print("\n   📝 Final Answer:")
                print(f"   {'-'*76}")
                print(f"   {state['final_answer']}")
                print(f"   {'-'*76}")


def example_all_tools_demo():
    """Example: Demonstrate activation of each specific tool"""
    print("\n" + "=" * 80)
    print("TOOL ACTIVATION DEMONSTRATION")
    print("=" * 80)
    print("This demo sends questions specifically designed to trigger each tool.")
    
    client = AgenticPipelineClient()
    
    # Define tool-specific test cases
    test_cases = [
        {
            "tool": "WEB SEARCH (Google Search)",
            "query": "What are the latest AI hardware releases in 2026?",
            "note": "Triggered by current events/lack of specific URL."
        },
        {
            "tool": "WEB CRAWLER (Targeted Scrape)",
            "query": "Summarize the key features from this page: https://www.python.org/about/",
            "note": "Triggered by the presence of an explicit URL."
        },
        {
            "tool": "GUITAR GALLERY TEST",
            "query": "Extract the contact information and location from https://www.guitargallery.com.sg/",
            "note": "Testing targeted crawl on a specific commercial site."
        },
        {
            "tool": "CALCULATOR",
            "query": "What is 15% of 2500 multiplied by 3?",
            "note": "Triggered by mathematical keywords and numbers."
        },
        {
            "tool": "INTERNAL RETRIEVAL",
            "query": "According to our internal PDF documents, what are the core lessons of Rich Dad Poor Dad?",
            "note": "Triggered by terms like 'internal' or 'documents'."
        }
    ]
    
    for test in test_cases:
        print(f"\n🚀 Testing tool: {test['tool']}")
        print(f"📝 Query: \"{test['query']}\"")
        print(f"💡 Expected because: {test['note']}")
        
        try:
            result = client.query(test['query'], temperature=0.1)
            print(f"🎯 Route Chosen: {result.get('routing_decision', 'N/A')}")
            print(f"✅ Preview: {result['final_answer'][:150]}...")
        except Exception as e:
            print(f"❌ Failed: {e}")


def example_guitar_gallery():
    """Example: Specific web crawl test for Guitar Gallery"""
    print("\n" + "=" * 80)
    print("GUITAR GALLERY ADVANCED CRAWL TEST")
    print("=" * 80)
    
    client = AgenticPipelineClient()
    query = "What acoustic guitars are currently featured on https://www.guitargallery.com.sg/ and what are their prices?"
    
    print(f"🚀 Sending individual query: \"{query}\"")
    print("⏳ This uses Crawl4AI (JavaScript rendering), so it might take 5-10 seconds...")
    print("-" * 80)
    
    # Using streaming for better feedback
    routing_used = None
    final_answer = None
    for event in client.stream_query(query, temperature=0.1):
        if 'node' in event:
            node = event.get('node')
            state = event.get('state', {})
            
            # Show routing decision if present
            if state.get('routing_decision'):
                routing_used = state['routing_decision']
                print(f"\n📍 Node: {node}")
                print(f"   🔀 Decision: {routing_used}")
            elif node:
                print(f"\n📍 Node: {node}")
            
            # Capture final answer if present
            if state.get('final_answer'):
                final_answer = state['final_answer']
                
        elif event.get('event') == 'complete':
            print("\n✅ FINISHED")
            if final_answer:
                print(f"\n📝 FINAL ANSWER:\n{final_answer}")
            print(f"\nTool Used: {routing_used}")
        elif event.get('event') == 'error':
            print(f"\n❌ ERROR: {event.get('error')}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("LANGCHAIN AGENTIC PIPELINE - CLIENT EXAMPLES")
    print("=" * 80)
    
    try:
        # Uncomment the examples you want to run
        
        # Basic examples
        # example_non_streaming()
        # example_streaming()
        # example_with_chat_history()
        # example_error_handling()
        
        # Rich Dad Poor Dad knowledge base examples
        # example_rich_dad_poor_dad_questions()
        # example_rich_dad_streaming() 
        
        # Tool activation demonstration
        # example_all_tools_demo()
        
        # Individual targeted crawl test
        example_guitar_gallery()
        
        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETED!")
        print("=" * 80 + "\n")
    
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API")
        print("   Make sure the API is running: python api.py")
        print("   Or: uvicorn api:app --reload --port 8000\n")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")

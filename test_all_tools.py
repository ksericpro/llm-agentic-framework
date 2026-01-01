"""
Test script to demonstrate when each tool (web search, web crawler, calculator, internal retrieval) is activated
Each question is designed to trigger a specific tool in the router agent
"""

import requests
import json
from typing import Dict


class AgenticPipelineClient:
    """Client for interacting with the LangChain Agentic Pipeline API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def query(self, query: str, temperature: float = 0.7) -> Dict:
        """Send a non-streaming query to the pipeline"""
        payload = {
            "query": query,
            "chat_history": [],
            "stream": False,
            "model": "gpt-4o-mini",
            "temperature": temperature
        }
        
        response = self.session.post(
            f"{self.base_url}/api/query",
            json=payload
        )
        response.raise_for_status()
        return response.json()


def test_web_search():
    """Test questions that should activate WEB SEARCH tool"""
    print("\n" + "=" * 80)
    print("🔍 TEST 1: WEB SEARCH (Google Search)")
    print("=" * 80)
    print("\nThese questions should trigger the 'web_search' tool")
    print("(Current events, news, general research without specific URLs)\n")
    
    client = AgenticPipelineClient()
    
    questions = [
        "What are the latest developments in artificial intelligence in 2026?",
        "Who won the Nobel Prize in Physics this year?",
        "What's the current weather in Tokyo?",
        "Find information about the latest iPhone model"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'─' * 80}")
        print(f"Question {i}: {question}")
        print('─' * 80)
        
        try:
            result = client.query(question, temperature=0.3)
            
            print(f"\n🔀 Routing Decision: {result.get('routing_decision', 'N/A')}")
            print(f"🎯 Intent: {result.get('intent', 'N/A')}")
            print(f"\n✅ Answer:\n{result['final_answer'][:300]}...")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")


def test_web_crawler():
    """Test questions that should activate WEB CRAWLER tool"""
    print("\n" + "=" * 80)
    print("🕷️  TEST 2: WEB CRAWLER (Targeted Crawl)")
    print("=" * 80)
    print("\nThese questions should trigger the 'targeted_crawl' tool")
    print("(Questions with EXPLICIT URLs to scrape/summarize)\n")
    
    client = AgenticPipelineClient()
    
    questions = [
        "Summarize this article: https://en.wikipedia.org/wiki/Artificial_intelligence",
        "What does https://www.python.org/about/ say about Python?",
        "Extract the main points from https://openai.com/blog",
        "Analyze the content at https://github.com/features"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'─' * 80}")
        print(f"Question {i}: {question}")
        print('─' * 80)
        
        try:
            result = client.query(question, temperature=0.3)
            
            print(f"\n🔀 Routing Decision: {result.get('routing_decision', 'N/A')}")
            print(f"🎯 Intent: {result.get('intent', 'N/A')}")
            print(f"\n✅ Answer:\n{result['final_answer'][:300]}...")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")


def test_calculator():
    """Test questions that should activate CALCULATOR tool"""
    print("\n" + "=" * 80)
    print("🧮 TEST 3: CALCULATOR")
    print("=" * 80)
    print("\nThese questions should trigger the 'calculator' tool")
    print("(Math calculations, conversions, formulas)\n")
    
    client = AgenticPipelineClient()
    
    questions = [
        "What is 234 multiplied by 567?",
        "Calculate the square root of 144",
        "What's 15% of 2500?",
        "Convert 100 kilometers to miles"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'─' * 80}")
        print(f"Question {i}: {question}")
        print('─' * 80)
        
        try:
            result = client.query(question, temperature=0.3)
            
            print(f"\n🔀 Routing Decision: {result.get('routing_decision', 'N/A')}")
            print(f"🎯 Intent: {result.get('intent', 'N/A')}")
            print(f"\n✅ Answer:\n{result['final_answer']}")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")


def test_internal_retrieval():
    """Test questions that should activate INTERNAL RETRIEVAL tool"""
    print("\n" + "=" * 80)
    print("📖 TEST 4: INTERNAL RETRIEVAL (PDF Knowledge Base)")
    print("=" * 80)
    print("\nThese questions should trigger the 'internal_retrieval' tool")
    print("(Questions about internal documents, company data, uploaded PDFs)\n")
    
    client = AgenticPipelineClient()
    
    questions = [
        "What does our internal documentation say about LangChain?",
        "According to our knowledge base, what are vector stores?",
        "What information do we have about agents in our documents?",
        "Search our internal database for information about RAG"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'─' * 80}")
        print(f"Question {i}: {question}")
        print('─' * 80)
        
        try:
            result = client.query(question, temperature=0.3)
            
            print(f"\n🔀 Routing Decision: {result.get('routing_decision', 'N/A')}")
            print(f"🎯 Intent: {result.get('intent', 'N/A')}")
            print(f"\n✅ Answer:\n{result['final_answer'][:300]}...")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")


def test_all_tools_summary():
    """Run all tests and show summary"""
    print("\n" + "=" * 80)
    print("🚀 TESTING ALL TOOLS IN AGENTIC FRAMEWORK")
    print("=" * 80)
    print("\nThis script will test 4 different tools:")
    print("  1. 🔍 Web Search (Google Search)")
    print("  2. 🕷️  Web Crawler (Targeted URL scraping)")
    print("  3. 🧮 Calculator (Math & conversions)")
    print("  4. 📖 Internal Retrieval (PDF knowledge base)")
    print("\nEach test will show which tool was activated by the Router Agent.")
    print("=" * 80)
    
    try:
        # Test each tool
        test_web_search()
        test_web_crawler()
        test_calculator()
        test_internal_retrieval()
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ ALL TOOL TESTS COMPLETED!")
        print("=" * 80)
        print("\n📝 Summary:")
        print("  • Web Search: Activated for current events, news, general research")
        print("  • Web Crawler: Activated when explicit URLs are provided")
        print("  • Calculator: Activated for mathematical calculations")
        print("  • Internal Retrieval: Activated for internal/uploaded documents")
        print("\n" + "=" * 80 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API")
        print("   Make sure the API is running:")
        print("   → python api.py")
        print("   → OR: uvicorn api:app --reload --port 8000\n")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")


if __name__ == "__main__":
    # Run all tests
    test_all_tools_summary()

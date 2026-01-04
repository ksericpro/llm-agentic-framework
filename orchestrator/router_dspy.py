import dspy
import os
from dotenv import load_dotenv
from typing import Literal

# 1. Setup & Configuration
# Load environment variables
load_dotenv()

# Configure DSPy
# We'll use the same model as the main pipeline (gpt-4o-mini or similar)
# Ensure OPENAI_API_KEY is in your .env
turbo = dspy.LM('openai/gpt-4o-mini', max_tokens=1000)
dspy.configure(lm=turbo)

# 2. Define the Signature
class RouterSignature(dspy.Signature):
    """
    Analyze the user's query and conversation history to decide the best tool to use.
    
    Tools:
    - 'internal_retrieval': For questions about books, PDFs, internal docs, or specific titles like 'Rich Dad Poor Dad'.
    - 'web_search': For current events, news, or general info not in our docs.
    - 'targeted_crawl': ONLY if a specific URL (http://...) is provided to extract content from.
    - 'calculator': For math problems.
    - 'translate': For translation requests.
    """
    
    query = dspy.InputField(desc="The user's latest question or command")
    chat_history = dspy.InputField(desc="Recent conversation context (optional)", format=str)
    
    # The output we want: A tool name and the reasoning
    reasoning = dspy.OutputField(desc="Why this tool was chosen")
    tool = dspy.OutputField(desc="The selected tool name", prefix="Tool:")
    target_url = dspy.OutputField(desc="If tool is targeted_crawl, the URL. Else 'None'")
    search_query = dspy.OutputField(desc="If tool is web_search or internal_retrieval, the search query. Else 'None'")
    target_language = dspy.OutputField(desc="If tool is translate, the language. Else 'None'")

# 3. Define the Module
class RouterModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.prog = dspy.ChainOfThought(RouterSignature)
    
    def forward(self, query, chat_history=""):
        return self.prog(query=query, chat_history=chat_history)

# 4. Training Data (Examples)
# We provide clear examples to guide the optimizer
train_examples = [
    dspy.Example(
        query="What is the price of Bitcoin today?", 
        chat_history="", 
        tool="web_search",
        reasoning="The user is asking for real-time information (today's price) which requires external data.",
        target_url="None",
        search_query="current bitcoin price",
        target_language="None"
    ).with_inputs("query", "chat_history"),
    
    dspy.Example(
        query="Summarize the key points of Rich Dad Poor Dad.", 
        chat_history="", 
        tool="internal_retrieval",
        reasoning="The user is asking about a specific book title that is likely in the internal knowledge base.",
        target_url="None",
        search_query="Rich Dad Poor Dad key points summary",
        target_language="None"
    ).with_inputs("query", "chat_history"),
    
    dspy.Example(
        query="Calculate 25 * 48 + 100", 
        chat_history="", 
        tool="calculator",
        reasoning="The query is a mathematical expression.",
        target_url="None",
        search_query="None",
        target_language="None"
    ).with_inputs("query", "chat_history"),
    
    dspy.Example(
        query="Translate 'Hello world' to Spanish", 
        chat_history="", 
        tool="translate",
        reasoning="The user explicitly requested translation.",
        target_url="None",
        search_query="None",
        target_language="Spanish"
    ).with_inputs("query", "chat_history"),
    
    dspy.Example(
        query="Extract the main article from https://example.com/news", 
        chat_history="", 
        tool="targeted_crawl",
        reasoning="The user provided a specific URL and asked to extract information from it.",
        target_url="https://example.com/news",
        search_query="None",
        target_language="None"
    ).with_inputs("query", "chat_history"),
    
    dspy.Example(
        query="What does the document say about risk management?", 
        chat_history="User: I uploaded the financial report.", 
        tool="internal_retrieval",
        reasoning="The user refers to 'the document' which implies internal context.",
        target_url="None",
        search_query="risk management in financial report",
        target_language="None"
    ).with_inputs("query", "chat_history"),
]

# 5. Optimization Function
def compile_router():
    """
    Compiles (optimizes) the RouterModule using BootstrapFewShot.
    Returns the compiled agent.
    """
    print("🚀 Compiling DSPy Router...")
    
    # Simple metric: Exact match on the tool name (case-insensitive)
    def validate_tool(example, pred, trace=None):
        return example.tool.lower() == pred.tool.lower().strip()

    # We use BootstrapFewShot to automatically select and format the best examples
    try:
        from dspy.teleprompt import BootstrapFewShot
    except ImportError:
        from dspy import BootstrapFewShot
    
    teleprompter = BootstrapFewShot(metric=validate_tool, max_bootstrapped_demos=4, max_labeled_demos=4)
    
    # Compile the agent
    compiled_router = teleprompter.compile(RouterModule(), trainset=train_examples)
    print("✅ Router Compiled Successfully!")
    return compiled_router

# 6. Usage Example
if __name__ == "__main__":
    # Compile the router
    router = compile_router()
    
    # Test queries
    test_queries = [
        "Who won the Super Bowl in 2024?",
        "What are the lessons in Chapter 1 of the uploaded PDF?",
        "What is 500 divided by 20?",
        "Read this page: https://news.ycombinator.com",
        "Say 'Good morning' in French"
    ]
    
    print("\n🧪 Testing Optimized Router:")
    for q in test_queries:
        print(f"\nQuery: {q}")
        pred = router(query=q)
        print(f"Reasoning: {pred.reasoning}")
        print(f"Tool: {pred.tool}")
        print(f"Search Query: {pred.search_query}")
        print(f"Target URL: {pred.target_url}")
        print(f"Target Language: {pred.target_language}")

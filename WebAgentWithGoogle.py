# Using Tavily API (recommended for simplicity and good results)
from langchain_community.tools.tavily_search import TavilySearchResults

class WebAgentWithGoogle:
    def __init__(self, llm):
        self.llm = llm
        # Initialize the search tool (Tavily uses multiple sources including Google)
        self.search_tool = TavilySearchResults(
            max_results=3,
            include_answer=True,
            include_raw_content=True,
            search_depth="advanced"  # Can also use "basic"
        )
        
        # Create an agent that decides WHEN and HOW to search
        self.agent = self._create_search_agent()
    
    def _create_search_agent(self):
        """Create a simple agent that can use the search tool."""
        tools = [self.search_tool]
        
        prompt = """You are a web research specialist. Your ONLY job is to answer questions by searching the web.
        
        Decision Rules:
        1. ALWAYS search if the question is about:
           - Current events, news, or recent developments
           - Live data (stock prices, weather, sports scores)
           - Information after
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal

class RoutingDecision(BaseModel):
    """Structured output for the router's decision."""
    tool: Literal["web_search", "targeted_crawl", "internal_retrieval", "calculator"] = Field(
        description="The tool best suited for the query."
    )
    reasoning: str = Field(description="Brief reasoning for the choice.")
    target_url: str | None = Field(
        description="If crawling, the specific URL to target. Otherwise None."
    )
    search_query: str | None = Field(
        description="If web searching, the optimized query string."
    )

class RouterAgent:
    def __init__(self, llm):
        self.llm = llm
        self.router_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Router Agent. Analyze the user's query and decide the best tool to use.
            
            **Decision Rules:**
            1. Use `web_search` for:
               - Questions about current events, news, or recent developments.
               - Open-ended "find information about X" queries.
               - When a specific source is NOT mentioned.
            
            2. Use `targeted_crawl` ONLY when:
               - The query EXPLICITLY mentions a specific, full URL (http://...).
               - The ask is to summarize, extract, or analyze content FROM that specific page.
            
            3. Use `internal_retrieval` for:
               - Questions about our internal documents, company data, or private knowledge base.
            
            4. Use `calculator` for:
               - Mathematical calculations, conversions, or formula-based problems.
            
            Return your decision as structured JSON."""),
            ("human", "User Query: {query}")
        ])
        # Create a chain that outputs the structured RoutingDecision
        self.chain = self.router_prompt | self.llm.with_structured_output(RoutingDecision)

    def route(self, user_query: str) -> RoutingDecision:
        """Main routing method."""
        decision = self.chain.invoke({"query": user_query})
        
        # You can add post-processing logic here
        # For example, validate URLs for crawl decisions
        if decision.tool == "targeted_crawl" and decision.target_url:
            if not self._is_valid_url(decision.target_url):
                # Fallback to search if the URL is invalid
                decision.tool = "web_search"
                decision.reasoning = "Invalid URL provided. Falling back to web search."
                decision.search_query = user_query
                decision.target_url = None
        elif decision.tool == "web_search" and not decision.search_query:
            # If search is chosen but no query is formulated, use the original
            decision.search_query = user_query
            
        return decision

    def _is_valid_url(self, url: str) -> bool:
        """Simple URL validation."""
        import re
        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return re.match(regex, url) is not None
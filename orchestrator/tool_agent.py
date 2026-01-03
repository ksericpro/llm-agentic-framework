"""
Tool Agent - Manages and executes various tools
Supports: Web search, calculators, API calls, custom tools
"""

from typing import List, Dict, Any, Optional, Callable
from langchain_core.tools import Tool

# Suppress annoying UserWarnings from langchain-tavily
import warnings
warnings.filterwarnings("ignore", message='Field name "output_schema" in "TavilyResearch" shadows an attribute in parent "BaseTool"')
warnings.filterwarnings("ignore", message='Field name "stream" in "TavilyResearch" shadows an attribute in parent "BaseTool"')

try:
    from langchain_tavily import TavilySearch
    TAVILY_NEW_PACKAGE = True
except ImportError:
    # Fallback to old package if new one not available
    from langchain_community.tools.tavily_search import TavilySearchResults
    TAVILY_NEW_PACKAGE = False
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field
from logger_config import setup_logger
import math
import requests
from crawler_agent import CrawlerAgent

logger = setup_logger("tool_agent")


# ============================================================================
# Custom Tool Definitions
# ============================================================================

class CalculatorInput(BaseModel):
    """Input for calculator tool"""
    expression: str = Field(description="Mathematical expression to evaluate")


def calculator_tool(expression: str) -> str:
    """
    Evaluate mathematical expressions safely
    
    Args:
        expression: Math expression (e.g., "2 + 2", "sqrt(16)", "sin(pi/2)")
    
    Returns:
        Result as string
    """
    try:
        # Safe evaluation with math functions
        allowed_names = {
            k: v for k, v in math.__dict__.items() 
            if not k.startswith("__")
        }
        allowed_names["abs"] = abs
        allowed_names["round"] = round
        
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"Result: {result}"
    
    except Exception as e:
        return f"Error: {str(e)}"


def web_scraper_tool(url: str) -> str:
    """
    Scrape content from a URL using CrawlerAgent
    """
    crawler = CrawlerAgent()
    return crawler.scrape(url)


def api_caller_tool(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> str:
    """
    Make API calls
    
    Args:
        endpoint: API endpoint URL
        method: HTTP method (GET, POST, etc.)
        data: Request payload for POST/PUT
    
    Returns:
        API response or error message
    """
    try:
        logger.info(f"Calling API: {method} {endpoint}")
        
        if method.upper() == "GET":
            response = requests.get(endpoint, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(endpoint, json=data, timeout=10)
        else:
            return f"Unsupported method: {method}"
        
        response.raise_for_status()
        return f"API Response ({response.status_code}):\n{response.text[:1000]}"
    
    except Exception as e:
        logger.error(f"API call error: {e}")
        return f"Error calling API: {str(e)}"


# ============================================================================
# Tool Agent Class
# ============================================================================

class ToolAgent:
    """
    Specialist agent for executing various tools.
    Manages tool selection, execution, and result formatting.
    """
    
    def __init__(self, llm=None, enable_web_search: bool = True):
        """
        Initialize the Tool Agent
        
        Args:
            llm: Language model for tool selection
            enable_web_search: Whether to enable web search tool
        """
        self.llm = llm
        self.tools = []
        self._init_tools(enable_web_search)
        
        # Create agent executor if LLM is provided
        if self.llm:
            self.agent_executor = self._create_agent_executor()
        else:
            self.agent_executor = None
    
    def _init_tools(self, enable_web_search: bool):
        """Initialize available tools"""
        
        # Calculator tool
        calculator = Tool(
            name="calculator",
            description="Useful for mathematical calculations. Input should be a math expression like '2+2' or 'sqrt(16)'",
            func=calculator_tool
        )
        self.tools.append(calculator)
        
        # Web scraper tool
        scraper = Tool(
            name="web_scraper",
            description="Scrapes content from a given URL. Input should be a valid URL starting with http:// or https://",
            func=web_scraper_tool
        )
        self.tools.append(scraper)
        
        # API caller tool
        api_caller = Tool(
            name="api_caller",
            description="Makes HTTP API calls. Input should be a JSON string with 'endpoint', 'method', and optional 'data' fields",
            func=lambda x: api_caller_tool(**eval(x))
        )
        self.tools.append(api_caller)
        
        # Web search tool (Tavily)
        if enable_web_search:
            try:
                if TAVILY_NEW_PACKAGE:
                    web_search = TavilySearch(
                        max_results=5
                    )
                else:
                    web_search = TavilySearchResults(
                        max_results=5,
                        include_answer=True,
                        include_raw_content=True,
                        search_depth="advanced"
                    )
                self.tools.append(web_search)
                logger.info(f"Web search tool enabled ({'TavilySearch' if TAVILY_NEW_PACKAGE else 'TavilySearchResults'})")
            except Exception as e:
                logger.warning(f"Could not enable web search: {e}")
        
        logger.info(f"Initialized {len(self.tools)} tools: {[t.name for t in self.tools]}")
    
    def _create_agent_executor(self):
        """Create an agent executor for autonomous tool usage"""
        
        # Note: The system prompt is now handled differently in newer LangGraph versions
        # The agent will use the tools' descriptions to understand how to use them
        
        # Create react agent using LangGraph
        agent_executor = create_react_agent(
            self.llm, 
            self.tools
        )
        
        return agent_executor
    
    def execute_tool(self, tool_name: str, tool_input: str) -> str:
        """
        Execute a specific tool by name
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input for the tool
        
        Returns:
            Tool execution result
        """
        logger.info(f"Executing tool: {tool_name} with input: {tool_input[:100]}...")
        
        # Find the tool
        tool = next((t for t in self.tools if t.name == tool_name), None)
        
        if not tool:
            available = [t.name for t in self.tools]
            return f"Error: Tool '{tool_name}' not found. Available tools: {available}"
        
        try:
            result = tool.func(tool_input)
            logger.info(f"Tool execution successful: {len(str(result))} chars returned")
            return result
        
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"Error executing {tool_name}: {str(e)}"
    
    def execute_with_agent(self, query: str, chat_history: List = None) -> Dict[str, Any]:
        """
        Use the agent executor to autonomously select and use tools
        
        Args:
            query: User query
            chat_history: Previous conversation messages
        
        Returns:
            Dictionary with output and intermediate steps
        """
        if not self.agent_executor:
            return {
                "output": "Error: Agent executor not initialized (LLM required)",
                "intermediate_steps": []
            }
        
        logger.info(f"Agent executing query: {query[:100]}...")
        
        try:
            # Convert chat history to messages format
            messages = []
            if chat_history:
                for msg in chat_history:
                    if isinstance(msg, (HumanMessage, AIMessage)):
                        messages.append(msg)
                    elif isinstance(msg, dict):
                        if msg.get("role") == "user":
                            messages.append(HumanMessage(content=msg.get("content", "")))
                        elif msg.get("role") == "assistant":
                            messages.append(AIMessage(content=msg.get("content", "")))
            
            # Add current query
            messages.append(HumanMessage(content=query))
            
            # Invoke the LangGraph agent
            result = self.agent_executor.invoke({"messages": messages})
            
            # Extract the final response
            final_message = result["messages"][-1]
            output = final_message.content if hasattr(final_message, 'content') else str(final_message)
            
            logger.info("Agent execution complete")
            return {
                "output": output,
                "intermediate_steps": result.get("messages", []),
                "messages": result.get("messages", [])
            }
        
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            return {
                "output": f"Error: {str(e)}",
                "intermediate_steps": []
            }
    
    def web_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform web search using Tavily
        
        Args:
            query: Search query
            max_results: Maximum number of results
        
        Returns:
            List of search results
        """
        logger.info(f"Web search: {query}")
        
        # Find Tavily tool
        tavily_tool = next(
            (t for t in self.tools if "tavily" in t.name.lower()),
            None
        )
        
        if not tavily_tool:
            logger.warning("Web search tool not available")
            return []
        
        try:
            print("      [TOOL] 🌍 Calling Tavily Search Engine...")
            results = tavily_tool.func({"query": query})
            
            if isinstance(results, list):
                print(f"      [TOOL] ✅ Found {len(results)} results from Tavily.")
                return results[:max_results]
            else:
                print("      [TOOL] ✅ Found 1 result from Tavily.")
                return [results]
        
        except Exception as e:
            logger.error(f"Web search error: {e}")
            print(f"      [TOOL] ❌ Web search failed: {e}")
            return []
    
    def calculate(self, expression: str) -> str:
        """
        Perform mathematical calculation
        
        Args:
            expression: Math expression
        
        Returns:
            Calculation result
        """
        return self.execute_tool("calculator", expression)
    
    def scrape_url(self, url: str) -> str:
        """
        Scrape content from URL using CrawlerAgent
        
        Args:
            url: URL to scrape
        
        Returns:
            Scraped content
        """
        crawler = CrawlerAgent()
        return crawler.scrape(url)
    
    def add_custom_tool(
        self,
        name: str,
        description: str,
        func: Callable
    ) -> bool:
        """
        Add a custom tool to the agent
        
        Args:
            name: Tool name
            description: Tool description for LLM
            func: Tool function
        
        Returns:
            Success status
        """
        try:
            tool = Tool(
                name=name,
                description=description,
                func=func
            )
            self.tools.append(tool)
            
            # Recreate agent executor if it exists
            if self.llm:
                self.agent_executor = self._create_agent_executor()
            
            logger.info(f"Added custom tool: {name}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding custom tool: {e}")
            return False
    
    def list_tools(self) -> List[Dict[str, str]]:
        """
        List all available tools
        
        Returns:
            List of tool information
        """
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools
        ]
    
    def format_tool_results(self, results: Any) -> str:
        """
        Format tool results for context injection
        
        Args:
            results: Tool execution results
        
        Returns:
            Formatted string
        """
        if isinstance(results, list):
            formatted = []
            for i, result in enumerate(results):
                if isinstance(result, dict):
                    content = result.get("content", "") or result.get("snippet", "")
                    url = result.get("url", "")
                    formatted.append(f"[Result {i+1}]\nURL: {url}\n{content}")
                else:
                    formatted.append(f"[Result {i+1}]\n{str(result)}")
            return "\n\n".join(formatted)
        else:
            return str(results)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    from langchain_openai import ChatOpenAI
    
    # Initialize
    llm = ChatOpenAI(model="gpt-4o-mini")
    tool_agent = ToolAgent(llm=llm, enable_web_search=True)
    
    # List available tools
    print("Available tools:")
    for tool in tool_agent.list_tools():
        print(f"  - {tool['name']}: {tool['description']}")
    
    # Execute specific tool
    print("\n1. Calculator:")
    result = tool_agent.calculate("sqrt(144) + 10")
    print(f"   {result}")
    
    # Use agent to autonomously select tools
    print("\n2. Agent execution:")
    result = tool_agent.execute_with_agent(
        "What is 25% of 480, and then search the web for current AI news"
    )
    print(f"   Output: {result['output'][:200]}...")
    
    # Web search
    print("\n3. Web search:")
    results = tool_agent.web_search("LangChain framework", max_results=2)
    print(f"   Found {len(results)} results")

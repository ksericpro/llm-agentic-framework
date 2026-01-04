import dspy
from router_agent import RoutingDecision
from router_dspy import compile_router, RouterModule
from logger_config import setup_logger

logger = setup_logger("router_dspy")

# Singleton to hold the compiled router so we don't re-compile on every request
_COMPILED_ROUTER = None

def get_or_compile_router():
    global _COMPILED_ROUTER
    if _COMPILED_ROUTER is None:
        logger.info("⚙️ Compiling DSPy Router (First Run)...")
        _COMPILED_ROUTER = compile_router()
    return _COMPILED_ROUTER

class RouterAgent:
    def __init__(self, llm):
        # We accept llm to match the interface, but we use the global DSPy config
        # Ensure DSPy is configured (it should be if this module is imported after setup)
        self.router = get_or_compile_router()

    def route(self, user_query: str, chat_history: list = None, summary: str = "") -> RoutingDecision:
        """
        Routes the query using the DSPy optimized agent.
        """
        logger.info(f"DSPy Routing query: {user_query[:100]}...")
        
        # Convert chat history list to string if needed
        history_str = str(chat_history) if chat_history else ""
        
        # Run the DSPy agent
        pred = self.router(query=user_query, chat_history=history_str)
        
        # Map DSPy output to RoutingDecision Pydantic model
        # We need to handle "None" strings and clean up
        
        def clean(val):
            if not val or str(val).lower() == "none":
                return None
            return str(val).strip()

        tool = clean(pred.tool)
        # Fallback if tool is invalid or None
        if tool not in ["web_search", "targeted_crawl", "internal_retrieval", "calculator", "translate"]:
            logger.warning(f"DSPy returned invalid tool '{tool}', defaulting to web_search")
            tool = "web_search"

        return RoutingDecision(
            tool=tool,
            reasoning=clean(pred.reasoning) or "DSPy determined this tool.",
            target_url=clean(pred.target_url),
            search_query=clean(pred.search_query),
            target_language=clean(pred.target_language)
        )

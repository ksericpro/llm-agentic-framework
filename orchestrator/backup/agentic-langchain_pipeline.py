"""
LangChain Agentic Pipeline with LangGraph
Implements a complete agentic workflow with streaming support
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from typing import TypedDict, Annotated, Sequence, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langfuse.langchain import CallbackHandler
import operator
import logging
from logger_config import setup_logger

# Import your existing agents
from router_agent import RouterAgent, RoutingDecision
from generator_agent import GeneratorAgent
from intentplanning_agent import IntentPlanningAgent, PlanSchema
from critic_agent import CriticAgent
from retriever_agent import RetrieverAgent
from tool_agent import ToolAgent

# Configure logging
logger = setup_logger("pipeline")

# Initialize Langfuse Callback Handler
# It will automatically pick up credentials from environment variables
try:
    langfuse_handler = CallbackHandler()
    logger.info("✅ Langfuse callback handler initialized")
except Exception as e:
    logger.warning(f"⚠️ Langfuse initialization skipped: {str(e)}")
    langfuse_handler = None


# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    """
    The state object that flows through the entire pipeline.
    Each agent reads from and writes to this state.
    """
    # Input
    query: str
    chat_history: Annotated[Sequence[BaseMessage], operator.add]
    llm: ChatOpenAI  # LLM instance passed through the pipeline
    
    # Router outputs
    routing_decision: RoutingDecision | None
    
    # Intent/Planning outputs
    intent: str | None
    plan: PlanSchema | None
    
    # Data retrieval outputs
    retrieved_context: List[str]
    web_search_results: List[Dict[str, Any]]
    
    # Generator outputs
    draft_answer: str | None
    
    # Critic outputs
    critique: Dict[str, Any] | None
    needs_revision: bool
    revision_count: int
    
    # Final output
    final_answer: str | None
    citations: List[int]
    
    # Metadata
    error: str | None


# ============================================================================
# Agent Node Functions
# ============================================================================

def router_node(state: AgentState) -> AgentState:
    """
    Router Agent: Determines which tool/approach to use
    """
    logger.info("🔀 Router Agent: Analyzing query...")
    
    try:
        router = RouterAgent(llm=state.get("llm"))
        decision = router.route(
            state["query"], 
            chat_history=list(state.get("chat_history", []))
        )
        
        logger.info(f"✅ Routing decision: {decision.tool} - {decision.reasoning}")
        
        return {
            **state,
            "routing_decision": decision
        }
    except Exception as e:
        logger.error(f"❌ Router error: {str(e)}")
        return {**state, "error": f"Router failed: {str(e)}"}


def intent_planning_node(state: AgentState) -> AgentState:
    """
    Intent & Planning Agent: Analyzes intent and creates execution plan
    """
    logger.info("🎯 Intent Planning Agent: Creating execution plan...")
    
    try:
        intent_agent = IntentPlanningAgent(llm=state.get("llm"))
        plan = intent_agent.analyze(
            state["query"],
            chat_history=list(state.get("chat_history", []))
        )
        
        logger.info(f"✅ Intent: {plan.intent}, Steps: {len(plan.steps)}")
        
        return {
            **state,
            "intent": plan.intent,
            "plan": plan
        }
    except Exception as e:
        logger.error(f"❌ Intent planning error: {str(e)}")
        return {**state, "error": f"Intent planning failed: {str(e)}"}


def retrieval_node(state: AgentState) -> AgentState:
    """
    Retrieval Node: Fetches data based on routing decision using dedicated agents
    """
    logger.info("📚 Retrieval Node: Fetching relevant data...")
    
    decision = state.get("routing_decision")
    retrieved_context = []
    web_results = []
    
    try:
        # Initialize agents
        llm = state.get("llm")
        tool_agent = ToolAgent(llm=llm, enable_web_search=True)
        retriever_agent = RetrieverAgent(llm=llm)
        
        # Refine query for retrieval if history exists
        chat_history = list(state.get("chat_history", []))
        search_query = retriever_agent.refine_query(state["query"], chat_history)
        
        if decision and decision.tool == "web_search":
            # Use ToolAgent for web search
            logger.info(f"🔍 Using ToolAgent for web search with query: {search_query}")
            
            web_results = tool_agent.web_search(search_query, max_results=5)
            
            # Format results for context
            if web_results:
                formatted = tool_agent.format_tool_results(web_results)
                retrieved_context.append(formatted)
            
            logger.info(f"✅ Retrieved {len(web_results)} web results")
        
        elif decision and decision.tool == "targeted_crawl":
            # Use ToolAgent for URL scraping
            logger.info(f"🕷️ Using ToolAgent to crawl URL: {decision.target_url}")
            
            if decision.target_url:
                scraped_content = tool_agent.scrape_url(decision.target_url)
                retrieved_context.append(scraped_content)
                logger.info("✅ URL crawled successfully")
        
        elif decision and decision.tool == "internal_retrieval":
            # Use RetrieverAgent for vector store retrieval
            logger.info(f"📖 Using RetrieverAgent for internal documents with query: {search_query}")
            
            docs = retriever_agent.retrieve(search_query, top_k=5)
            
            if docs:
                formatted_docs = retriever_agent.format_documents(docs)
                retrieved_context.extend(formatted_docs)
                logger.info(f"✅ Retrieved {len(docs)} internal documents")
            else:
                logger.warning("No internal documents found")
                retrieved_context.append("No relevant internal documents found.")
        
        elif decision and decision.tool == "calculator":
            # Use ToolAgent for calculations
            logger.info("🧮 Using ToolAgent for calculation...")
            
            result = tool_agent.calculate(state["query"])
            retrieved_context.append(f"Calculation result: {result}")
            logger.info("✅ Calculation completed")
        
        else:
            # Default: use query as context
            logger.warning("No specific tool selected, using query as context")
            retrieved_context.append(state["query"])
        
        return {
            **state,
            "retrieved_context": retrieved_context,
            "web_search_results": web_results
        }
    
    except Exception as e:
        logger.error(f"❌ Retrieval error: {str(e)}")
        return {**state, "error": f"Retrieval failed: {str(e)}"}



def generator_node(state: AgentState) -> AgentState:
    """
    Generator Agent: Synthesizes final answer
    """
    logger.info("✍️ Generator Agent: Creating answer...")
    
    try:
        generator = GeneratorAgent(llm=state.get("llm"))
        
        # Prepare instructions from plan
        instructions = "Generate a comprehensive answer."
        if state.get("plan"):
            instructions = f"Intent: {state['intent']}. Follow this plan: {state['plan']}"
        
        # Handle critique-based revision
        if state.get("critique") and state.get("needs_revision"):
            logger.info("🔄 Revising based on critique...")
            result = generator.handle_critique(
                state["draft_answer"],
                state["critique"]
            )
            answer = result if isinstance(result, str) else result.get("answer", "")
        else:
            # Initial generation
            result = generator.generate(
                question=state["query"],
                instructions=instructions,
                context=state.get("retrieved_context", []),
                chat_history=list(state.get("chat_history", []))
            )
            answer = result.get("answer", "")
        
        logger.info(f"✅ Generated answer ({len(answer)} chars)")
        
        return {
            **state,
            "draft_answer": answer,
            "citations": result.get("citations", []) if isinstance(result, dict) else []
        }
    
    except Exception as e:
        logger.error(f"❌ Generator error: {str(e)}")
        return {**state, "error": f"Generator failed: {str(e)}"}


def critic_node(state: AgentState) -> AgentState:
    """
    Critic Agent: Reviews answer quality
    """
    logger.info("🔍 Critic Agent: Reviewing answer quality...")
    
    try:
        critic = CriticAgent(llm=state.get("llm"))
        
        critique = critic.review(
            original_query=state["query"],
            draft_answer=state["draft_answer"],
            source_data=state.get("retrieved_context", [])
        )
        
        needs_revision = critique.get("needs_correction", False)
        
        # Limit revisions to prevent infinite loops
        revision_count = state.get("revision_count", 0)
        if revision_count >= 2:
            logger.warning("⚠️ Max revisions reached, accepting current answer")
            needs_revision = False
        
        logger.info(f"✅ Critique complete. Needs revision: {needs_revision}")
        
        return {
            **state,
            "critique": critique,
            "needs_revision": needs_revision,
            "revision_count": revision_count + 1 if needs_revision else revision_count
        }
    
    except Exception as e:
        logger.error(f"❌ Critic error: {str(e)}")
        # Don't fail the pipeline, just skip critique
        return {
            **state,
            "critique": {"needs_correction": False},
            "needs_revision": False
        }


def finalize_node(state: AgentState) -> AgentState:
    """
    Finalize: Prepares the final answer
    """
    logger.info("✨ Finalizing answer...")
    
    final_answer = state.get("draft_answer", "I apologize, but I couldn't generate an answer.")
    
    # Add citations if available
    if state.get("citations"):
        final_answer += f"\n\nCitations: {state['citations']}"
    
    return {
        **state,
        "final_answer": final_answer
    }


# ============================================================================
# Conditional Edge Functions
# ============================================================================

def should_revise(state: AgentState) -> str:
    """
    Determines if the answer needs revision based on critique
    """
    if state.get("error"):
        return "finalize"
    
    if state.get("needs_revision", False):
        logger.info("🔄 Routing back to generator for revision")
        return "revise"
    else:
        logger.info("✅ Answer approved, finalizing")
        return "finalize"


# ============================================================================
# Build the LangGraph Workflow
# ============================================================================

def create_agent_graph(llm: ChatOpenAI) -> StateGraph:
    """
    Creates the complete agent workflow graph
    """
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add all nodes
    workflow.add_node("router", router_node)
    workflow.add_node("intent_planning", intent_planning_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("finalize", finalize_node)
    
    # Define the flow
    workflow.set_entry_point("router")
    
    # Linear flow with conditional revision loop
    workflow.add_edge("router", "intent_planning")
    workflow.add_edge("intent_planning", "retrieval")
    workflow.add_edge("retrieval", "generator")
    workflow.add_edge("generator", "critic")
    
    # Conditional edge: revise or finalize
    workflow.add_conditional_edges(
        "critic",
        should_revise,
        {
            "revise": "generator",  # Loop back for revision
            "finalize": "finalize"
        }
    )
    
    # End after finalization
    workflow.add_edge("finalize", END)
    
    # Add memory/checkpointing
    memory = MemorySaver()
    
    # Compile the graph
    app = workflow.compile(checkpointer=memory)
    
    return app


# ============================================================================
# Main Execution Function
# ============================================================================

def run_agent_pipeline(
    query: str,
    llm: ChatOpenAI,
    chat_history: List[BaseMessage] = None,
    stream: bool = False
) -> Dict[str, Any]:
    """
    Runs the complete agent pipeline (non-streaming only)
    
    Args:
        query: User's question
        llm: Language model instance
        chat_history: Previous conversation messages
        stream: Whether to stream the response (deprecated, use stream_agent_pipeline instead)
    
    Returns:
        Dictionary with final_answer and metadata
    """
    # Create the graph
    app = create_agent_graph(llm)
    
    # Initialize state
    initial_state = {
        "query": query,
        "chat_history": chat_history or [],
        "llm": llm,
        "routing_decision": None,
        "intent": None,
        "plan": None,
        "retrieved_context": [],
        "web_search_results": [],
        "draft_answer": None,
        "critique": None,
        "needs_revision": False,
        "revision_count": 0,
        "final_answer": None,
        "citations": [],
        "error": None
    }
    
    # Run the pipeline (non-streaming only)
    config = {
        "configurable": {"thread_id": "default"},
        "callbacks": [langfuse_handler] if langfuse_handler else []
    }
    result = app.invoke(initial_state, config)
    return result


def stream_agent_pipeline(
    query: str,
    llm: ChatOpenAI,
    chat_history: List[BaseMessage] = None
):
    """
    Runs the complete agent pipeline in streaming mode (synchronous generator)
    
    Args:
        query: User's question
        llm: Language model instance
        chat_history: Previous conversation messages
    
    Yields:
        Events from the pipeline execution
    """
    # Create the graph
    app = create_agent_graph(llm)
    
    # Initialize state
    initial_state = {
        "query": query,
        "chat_history": chat_history or [],
        "llm": llm,
        "routing_decision": None,
        "intent": None,
        "plan": None,
        "retrieved_context": [],
        "web_search_results": [],
        "draft_answer": None,
        "critique": None,
        "needs_revision": False,
        "revision_count": 0,
        "final_answer": None,
        "citations": [],
        "error": None
    }
    
    # Run the pipeline in streaming mode
    config = {
        "configurable": {"thread_id": "default"},
        "callbacks": [langfuse_handler] if langfuse_handler else []
    }
    for event in app.stream(initial_state, config):
        yield event


# ============================================================================
# Streaming Generator for API
# ============================================================================

async def stream_agent_response(query: str, llm: ChatOpenAI):
    """
    Async generator for streaming responses
    """
    app = create_agent_graph(llm)
    
    initial_state = {
        "query": query,
        "chat_history": [],
        "llm": llm,
        "routing_decision": None,
        "intent": None,
        "plan": None,
        "retrieved_context": [],
        "web_search_results": [],
        "draft_answer": None,
        "critique": None,
        "needs_revision": False,
        "revision_count": 0,
        "final_answer": None,
        "citations": [],
        "error": None
    }
    
    config = {
        "configurable": {"thread_id": "default"},
        "callbacks": [langfuse_handler] if langfuse_handler else []
    }
    
    # Stream events
    async for event in app.astream(initial_state, config):
        # Extract the node name and state
        for node_name, node_state in event.items():
            yield {
                "node": node_name,
                "state": {
                    "draft_answer": node_state.get("draft_answer"),
                    "final_answer": node_state.get("final_answer"),
                    "routing_decision": str(node_state.get("routing_decision")),
                    "intent": node_state.get("intent"),
                    "error": node_state.get("error")
                }
            }

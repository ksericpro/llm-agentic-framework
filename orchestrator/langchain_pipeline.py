"""
LangChain Agentic Pipeline with LangGraph
Implements a complete agentic workflow with streaming support and persistent memory.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from typing import TypedDict, Sequence, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from logger_config import setup_logger

# Import your existing agents
from router_agent import RouterAgent, RoutingDecision
from generator_agent import GeneratorAgent
from intentplanning_agent import IntentPlanningAgent, PlanSchema
from critic_agent import CriticAgent
from retriever_agent import RetrieverAgent
from tool_agent import ToolAgent
from translation_agent import TranslationAgent

# Configure logging
logger = setup_logger("pipeline")

# Initialize Langfuse Observability
try:
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        LANGFUSE_ENABLED = True
        logger.info("📊 Langfuse observability enabled")
    else:
        LANGFUSE_ENABLED = False
        logger.warning("⚠️ Langfuse keys not set (observability disabled)")
except Exception as e:
    LANGFUSE_ENABLED = False
    logger.warning(f"⚠️ Langfuse check failed: {str(e)}")

# Initialize MongoDB Checkpointer
mongodb_client = None
mongodb_saver = None

def get_checkpointer():
    """
    Initializes and returns the MongoDB checkpointer if MONGO_URL is available.
    Falls back to MemorySaver otherwise.
    """
    global mongodb_client, mongodb_saver
    
    if mongodb_saver:
        return mongodb_saver
        
    mongo_url = os.getenv("MONGO_URL")
    if mongo_url:
        try:
            if mongodb_client is None:
                logger.info("🔌 Connecting to MongoDB for checkpointing...")
                mongodb_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
                mongodb_client.admin.command('ping')
            
            # Explicitly use 'checkpointing_db' which is the default for this version
            mongodb_saver = MongoDBSaver(mongodb_client, db_name="checkpointing_db")
            logger.info("✅ MongoDB checkpointer initialized")
            return mongodb_saver
        except Exception as e:
            logger.error(f"❌ Failed to initialize MongoDB checkpointer: {e}")
            mongodb_client = None
            
    logger.warning("⚠️ Using in-memory checkpointer (MemorySaver)")
    return MemorySaver()


def get_all_sessions() -> List[Dict[str, Any]]:
    """
    Fetches all unique session IDs and their latest summaries from MongoDB.
    """
    global mongodb_client
    
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        return []
        
    try:
        # Ensure client is initialized
        if mongodb_client is None:
            mongodb_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            mongodb_client.admin.command('ping')
            
        db = mongodb_client["checkpointing_db"]
        collection = db["checkpoints"]
        
        # Get unique thread_ids
        thread_ids = collection.distinct("thread_id")
        
        checkpointer = get_checkpointer()
        sessions = []
        
        # Fetch latest state for each thread
        for tid in thread_ids:
            try:
                config = {"configurable": {"thread_id": tid}}
                state = checkpointer.get(config)
                if state:
                    # Handle both CheckpointTuple and direct dict
                    if hasattr(state, 'checkpoint'):
                        checkpoint = state.checkpoint
                    elif isinstance(state, dict) and 'checkpoint' in state:
                        checkpoint = state['checkpoint']
                    else:
                        checkpoint = state
                    
                    # Extract values and timestamp
                    if isinstance(checkpoint, dict):
                        values = checkpoint.get("channel_values", {})
                        ts = checkpoint.get("ts", "")
                        summary = values.get("summary", "No summary available")
                        
                        sessions.append({
                            "session_id": tid,
                            "summary": summary,
                            "last_updated": ts
                        })
            except Exception as e:
                logger.warning(f"Could not parse session {tid}: {e}")
                
        # Sort by last_updated descending
        sessions.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        return sessions
    except Exception as e:
        logger.error(f"❌ Failed to fetch sessions: {e}")
        mongodb_client = None
        return []


def clear_all_sessions() -> bool:
    """
    Deletes all checkpoints and writes from MongoDB.
    """
    global mongodb_client
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        return False
        
    try:
        if mongodb_client is None:
            mongodb_client = MongoClient(mongo_url)
            
        db = mongodb_client["checkpointing_db"]
        # Clear both primary checkpoints and intermediate writes
        db["checkpoints"].delete_many({})
        db["checkpoint_writes"].delete_many({})
        db["checkpoint_blobs"].delete_many({}) # Some versions use this too
        
        logger.info("🗑️ All chat sessions cleared from MongoDB")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to clear sessions: {e}")
        return False


def get_session_state(thread_id: str) -> Dict[str, Any]:
    """
    Fetches the latest state for a specific session.
    """
    checkpointer = get_checkpointer()
    if isinstance(checkpointer, MemorySaver):
        return {}
        
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = checkpointer.get(config)
        if state:
            # Handle both CheckpointTuple and direct dict
            if hasattr(state, 'checkpoint'):
                checkpoint = state.checkpoint
            elif isinstance(state, dict) and 'checkpoint' in state:
                checkpoint = state['checkpoint']
            else:
                checkpoint = state
                
            if isinstance(checkpoint, dict):
                return checkpoint.get("channel_values", {})
        return {}
    except Exception as e:
        logger.error(f"❌ Failed to fetch session state: {e}")
        return {}


def clear_session_context(thread_id: str) -> bool:
    """
    Clears the chat history and summary for a specific session (forget command).
    The session ID remains active but context is reset.
    """
    global mongodb_client
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        logger.warning("⚠️ Cannot clear session context: MongoDB not configured")
        return False
        
    try:
        if mongodb_client is None:
            mongodb_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            
        db = mongodb_client["checkpointing_db"]
        
        # Delete all checkpoints and writes for this specific thread_id
        result_checkpoints = db["checkpoints"].delete_many({"thread_id": thread_id})
        result_writes = db["checkpoint_writes"].delete_many({"thread_id": thread_id})
        
        # Also try to delete from checkpoint_blobs if it exists
        try:
            db["checkpoint_blobs"].delete_many({"thread_id": thread_id})
        except Exception:
            pass  # Collection might not exist
        
        logger.info(f"🗑️ Cleared context for session '{thread_id}' ({result_checkpoints.deleted_count} checkpoints, {result_writes.deleted_count} writes)")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to clear session context: {e}")
        return False


# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    """
    The state object that flows through the entire pipeline.
    """
    # Input
    query: str
    chat_history: Sequence[BaseMessage]
    llm: ChatOpenAI
    
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
    
    # Translation outputs
    target_language: str | None
    global_target_language: str | None
    
    # Memory management
    summary: str
    
    # Metadata
    error: str | None


# ============================================================================
# Agent Node Functions
# ============================================================================

def summarize_node(state: AgentState) -> AgentState:
    """
    Summarization Node: Condenses old messages to save tokens.
    Implements hierarchical summarization for very long conversations (100+ messages).
    """
    history = state.get("chat_history", [])
    if len(history) < 10:
        return state

    logger.info(f"🧠 Summarizing conversation history ({len(history)} messages)...")
    
    messages_to_summarize = history[:-4]
    existing_summary = state.get("summary", "")
    
    # Hierarchical Summarization for very long conversations (100+ messages)
    if len(history) >= 100:
        logger.info("📚 Applying hierarchical summarization for long conversation...")
        
        # Split old messages into chunks of 20 for progressive summarization
        chunk_size = 20
        chunk_summaries = []
        
        for i in range(0, len(messages_to_summarize), chunk_size):
            chunk = messages_to_summarize[i:i+chunk_size]
            chunk_text = "\n".join([f"{msg.type}: {msg.content}" for msg in chunk])
            
            chunk_prompt = f"""
            Summarize this conversation segment concisely, preserving key facts:
            
            {chunk_text}
            
            Brief Summary:
            """
            
            try:
                chunk_response = state["llm"].invoke(chunk_prompt)
                chunk_summaries.append(chunk_response.content)
            except Exception as e:
                logger.warning(f"⚠️ Chunk summarization failed: {e}")
                continue
        
        # Now create a meta-summary from all chunk summaries
        meta_summary_prompt = f"""
        Create a comprehensive summary by combining these segment summaries.
        Preserve all important facts, decisions, user preferences, and context.
        
        Previous Summary: {existing_summary}
        
        New Segment Summaries:
        {chr(10).join([f"- {s}" for s in chunk_summaries])}
        
        Comprehensive Summary:
        """
        
        try:
            response = state["llm"].invoke(meta_summary_prompt)
            logger.info("✅ Hierarchical summarization complete")
            return {"summary": response.content}
        except Exception as e:
            logger.error(f"❌ Meta-summarization failed: {e}")
            return {}
    
    # Standard summarization for shorter conversations (10-99 messages)
    else:
        summary_prompt = f"""
        Distill the following conversation into a concise summary. 
        Include all key facts, decisions, and user preferences mentioned.
        
        Existing Summary: {existing_summary}
        
        New messages to incorporate:
        {messages_to_summarize}
        
        Concise Summary:
        """
        
        try:
            response = state["llm"].invoke(summary_prompt)
            return {"summary": response.content}
        except Exception as e:
            logger.error(f"❌ Summarization failed: {e}")
            return {}


def router_node(state: AgentState) -> AgentState:
    """
    Router Agent: Determines which tool/approach to use
    """
    logger.info("🔀 Router Agent: Analyzing query...")
    try:
        router = RouterAgent(llm=state.get("llm"))
        chat_history = list(state.get("chat_history", []))[-6:]
        decision = router.route(
            state["query"], 
            chat_history=chat_history,
            summary=state.get("summary", "")
        )
        logger.info(f"✅ Routing decision: {decision.tool}")
        return {"routing_decision": decision}
    except Exception as e:
        logger.error(f"❌ Router error: {str(e)}")
        return {"error": f"Router failed: {str(e)}"}


def intent_planning_node(state: AgentState) -> AgentState:
    """
    Intent & Planning Agent: Analyzes intent and creates execution plan
    """
    logger.info("🎯 Intent Planning Agent: Creating execution plan...")
    try:
        intent_agent = IntentPlanningAgent(llm=state.get("llm"))
        chat_history = list(state.get("chat_history", []))[-6:]
        plan = intent_agent.analyze(
            state["query"],
            chat_history=chat_history,
            summary=state.get("summary", "")
        )
        return {"intent": plan.intent, "plan": plan}
    except Exception as e:
        logger.error(f"❌ Intent planning error: {str(e)}")
        return {"error": f"Intent planning failed: {str(e)}"}


def retrieval_node(state: AgentState) -> AgentState:
    """
    Retrieval Node: Fetches data based on routing decision
    """
    logger.info("📚 Retrieval Node: Fetching relevant data...")
    decision = state.get("routing_decision")
    retrieved_context = []
    web_results = []
    
    try:
        llm = state.get("llm")
        tool_agent = ToolAgent(llm=llm, enable_web_search=True)
        retriever_agent = RetrieverAgent(llm=llm)
        
        chat_history = list(state.get("chat_history", []))[-6:]
        search_query = retriever_agent.refine_query(
            state["query"], 
            chat_history,
            summary=state.get("summary", "")
        )
        
        if decision and decision.tool == "web_search":
            logger.info(f"🌐 EXECUTION: Web Search for '{search_query}'")
            print(f"\n[AGENT] 🌐 Starting web search for: '{search_query}'...")
            web_results = tool_agent.web_search(search_query, max_results=5)
            if web_results:
                retrieved_context.append(tool_agent.format_tool_results(web_results))
                logger.info(f"✅ SEARCH COMPLETE: Found {len(web_results)} results")
                print(f"[AGENT] ✅ Web search complete. Found {len(web_results)} relevant results.\n")
            else:
                logger.warning("⚠️ SEARCH: No results found")
                print("[AGENT] ⚠️ No web search results found for the query.\n")
        elif decision and decision.tool == "targeted_crawl":
            if decision.target_url:
                logger.info(f"🕸️ EXECUTION: Targeted Crawl on {decision.target_url}")
                print(f"\n[AGENT] 🕸️ Starting targeted crawl for: {decision.target_url}...")
                content = tool_agent.scrape_url(decision.target_url)
                retrieved_context.append(content)
                logger.info(f"✅ CRAWL COMPLETE: Received {len(content)} chars")
                print(f"[AGENT] ✅ Targeted crawl complete. Length: {len(content)} characters.\n")
        elif decision and decision.tool == "internal_retrieval":
            logger.info(f"📚 EXECUTION: Internal RAG Retrieval for '{search_query}'")
            print(f"\n[AGENT] 📚 Searching internal knowledge base for: '{search_query}'...")
            docs = retriever_agent.retrieve(search_query, top_k=5)
            if docs:
                formatted_docs = retriever_agent.format_documents(docs)
                retrieved_context.extend(formatted_docs)
                logger.info(f"✅ RAG COMPLETE: Retrieved {len(docs)} documents")
                print(f"[AGENT] ✅ RAG retrieval complete. Retrieved {len(docs)} relevant document chunks.\n")
            else:
                logger.warning("⚠️ RAG: No relevant documents found")
                print("[AGENT] ⚠️ No relevant documents found in the knowledge base.\n")
        elif decision and decision.tool == "calculator":
            logger.info(f"🔢 EXECUTION: Calculator for '{state['query']}'")
            print(f"\n[AGENT] 🔢 Evaluating math expression: '{state['query']}'...")
            result = tool_agent.calculate(state["query"])
            retrieved_context.append(f"Calculation result: {result}")
            logger.info(f"✅ CALC COMPLETE: {result}")
            print(f"[AGENT] ✅ Calculation complete: {result}\n")
        else:
            retrieved_context.append(state["query"])
            
        return {"retrieved_context": retrieved_context, "web_search_results": web_results}
    except Exception as e:
        logger.error(f"❌ Retrieval error: {str(e)}")
        return {"error": f"Retrieval failed: {str(e)}"}


def translation_node(state: AgentState) -> AgentState:
    """
    Translation Agent: Translates text to target language
    """
    decision = state.get("routing_decision")
    target_lang = "Chinese"
    if decision and decision.tool == "translate" and decision.target_language:
        target_lang = decision.target_language
        
    logger.info(f"🈯 Translation Node: Translating to {target_lang}...")
    try:
        translator = TranslationAgent(llm=state.get("llm"))
        # We translate the query if no retrieved context or draft answer exists, 
        # otherwise we translate the retrieved context/draft answer.
        text_to_translate = state["query"]
        
        # If we have a draft answer (e.g. from generator), translate that
        if state.get("draft_answer"):
            text_to_translate = state["draft_answer"]
        elif state.get("retrieved_context"):
            text_to_translate = "\n".join(state["retrieved_context"])
            
        translated_text = translator.translate(text_to_translate, target_lang)
        return {"final_answer": translated_text, "target_language": target_lang}
    except Exception as e:
        logger.error(f"❌ Translation error: {str(e)}")
        return {"error": f"Translation failed: {str(e)}"}


def generator_node(state: AgentState) -> AgentState:
    """
    Generator Agent: Synthesizes final answer
    """
    logger.info("✍️ Generator Agent: Creating answer...")
    try:
        generator = GeneratorAgent(llm=state.get("llm"))
        instructions = f"Intent: {state.get('intent')}. Plan: {state.get('plan')}"
        
        if state.get("critique") and state.get("needs_revision"):
            answer = generator.handle_critique(state["draft_answer"], state["critique"])
            citations = []
        else:
            chat_history = list(state.get("chat_history", []))[-6:]
            result = generator.generate(
                question=state["query"],
                instructions=instructions,
                context=state.get("retrieved_context", []),
                chat_history=chat_history,
                summary=state.get("summary", "")
            )
            answer = result.get("answer", "")
            citations = result.get("citations", [])
            
        return {"draft_answer": answer, "citations": citations}
    except Exception as e:
        logger.error(f"❌ Generator error: {str(e)}")
        return {"error": f"Generator failed: {str(e)}"}


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
        needs_revision = critique.get("needs_correction", False) and state.get("revision_count", 0) < 2
        return {
            "critique": critique,
            "needs_revision": needs_revision,
            "revision_count": state.get("revision_count", 0) + (1 if needs_revision else 0)
        }
    except Exception as e:
        logger.error(f"❌ Critic error: {str(e)}")
        return {"needs_revision": False}


def finalize_node(state: AgentState) -> AgentState:
    """
    Finalize: Prepares the final answer and updates chat history for persistence.
    Supports universal translation if global_target_language is set.
    """
    logger.info("✨ Finalizing answer...")
    
    # 1. Determine base answer
    final_answer = state.get("final_answer")
    if not final_answer:
        final_answer = state.get("draft_answer", "I apologize, but I couldn't generate an answer.")
        if state.get("citations"):
            final_answer += f"\n\nCitations: {state['citations']}"
    
    # 2. Apply Global Translation if requested and not already done by translation_node
    global_lang = state.get("global_target_language")
    current_lang = state.get("target_language")
    
    if global_lang and global_lang.lower() not in ["english", "none", "en"]:
        if global_lang != current_lang:
            logger.info(f"🈯 Global Translation: Translating final answer to {global_lang}...")
            try:
                translator = TranslationAgent(llm=state.get("llm"))
                final_answer = translator.translate(final_answer, global_lang)
            except Exception as e:
                logger.error(f"❌ Global translation failed: {e}")
    
    # Update chat history for persistence
    current_history = list(state.get("chat_history", []))
    new_messages = [
        HumanMessage(content=state["query"]),
        AIMessage(content=final_answer)
    ]
    
    return {
        "final_answer": final_answer,
        "chat_history": current_history + new_messages
    }


# ============================================================================
# Conditional Edge Functions
# ============================================================================

def should_revise(state: AgentState) -> str:
    if state.get("error") or not state.get("needs_revision"):
        return "finalize"
    return "revise"


# ============================================================================
# Build the LangGraph Workflow
# ============================================================================

def create_agent_graph(llm: ChatOpenAI) -> StateGraph:
    workflow = StateGraph(AgentState)
    
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("router", router_node)
    workflow.add_node("intent_planning", intent_planning_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("translation", translation_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("finalize", finalize_node)
    
    workflow.set_entry_point("summarize")
    workflow.add_edge("summarize", "router")
    workflow.add_edge("router", "intent_planning")
    workflow.add_edge("intent_planning", "retrieval")
    
    # Conditional edge after retrieval: Translate or Generate?
    def route_after_retrieval(state: AgentState) -> str:
        decision = state.get("routing_decision")
        if decision and decision.tool == "translate":
            return "translate"
        return "generator"
        
    workflow.add_conditional_edges(
        "retrieval",
        route_after_retrieval,
        {"translate": "translation", "generator": "generator"}
    )
    
    workflow.add_edge("translation", "finalize")
    workflow.add_edge("generator", "critic")
    
    workflow.add_conditional_edges(
        "critic",
        should_revise,
        {"revise": "generator", "finalize": "finalize"}
    )
    workflow.add_edge("finalize", END)
    
    checkpointer = get_checkpointer()
    return workflow.compile(checkpointer=checkpointer)


# ============================================================================
# Execution Functions
# ============================================================================

def run_agent_pipeline(query: str, llm: ChatOpenAI, chat_history: List[BaseMessage] = None, thread_id: str = "default", stream: bool = False, target_language: str = None):
    app = create_agent_graph(llm)
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
        "target_language": None,
        "global_target_language": target_language,
        "summary": "",
        "error": None
    }
    
    callbacks = [CallbackHandler()] if LANGFUSE_ENABLED else []
    config = {
        "configurable": {"thread_id": thread_id}, 
        "callbacks": callbacks,
        "metadata": {"session_id": thread_id}
    }
    return app.invoke(initial_state, config)


def stream_agent_pipeline(query: str, llm: ChatOpenAI, chat_history: List[BaseMessage] = None, thread_id: str = "default", target_language: str = None):
    app = create_agent_graph(llm)
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
        "target_language": None,
        "global_target_language": target_language,
        "summary": "",
        "error": None
    }
    
    callbacks = [CallbackHandler()] if LANGFUSE_ENABLED else []
    config = {
        "configurable": {"thread_id": thread_id}, 
        "callbacks": callbacks,
        "metadata": {"session_id": thread_id}
    }
    for event in app.stream(initial_state, config):
        yield event


async def stream_agent_response(query: str, llm: ChatOpenAI, thread_id: str = "default", target_language: str = None):
    app = create_agent_graph(llm)
    
    # Load existing chat history and summary from checkpointer if available
    existing_state = get_session_state(thread_id)
    existing_history = existing_state.get("chat_history", []) if existing_state else []
    existing_summary = existing_state.get("summary", "") if existing_state else ""
    
    initial_state = {
        "query": query,
        "chat_history": existing_history,  # Use existing history instead of empty list
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
        "target_language": None,
        "global_target_language": target_language,
        "summary": existing_summary,  # Preserve existing summary
        "error": None
    }
    
    callbacks = [CallbackHandler()] if LANGFUSE_ENABLED else []
    config = {
        "configurable": {"thread_id": thread_id}, 
        "callbacks": callbacks,
        "metadata": {"session_id": thread_id}
    }
    
    async for event in app.astream(initial_state, config):
        for node_name, node_state in event.items():
            # Extract routing decision properly
            routing_decision = node_state.get("routing_decision")
            routing_str = None
            if routing_decision:
                if hasattr(routing_decision, 'tool'):
                    routing_str = routing_decision.tool
                else:
                    routing_str = str(routing_decision)
            
            yield {
                "node": node_name,
                "state": {
                    "draft_answer": node_state.get("draft_answer"),
                    "final_answer": node_state.get("final_answer"),
                    "routing_decision": routing_str,
                    "intent": node_state.get("intent"),
                    "summary": node_state.get("summary"),
                    "error": node_state.get("error")
                }
            }

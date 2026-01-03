"""
FastAPI Application for LangChain Agentic Pipeline
Provides REST API endpoints with streaming support
"""

import os
from dotenv import load_dotenv

# Load environment variables as early as possible
load_dotenv()

# Suppress annoying UserWarnings from langchain-tavily (shadowing attributes)
import warnings
warnings.filterwarnings("ignore", message='Field name "output_schema" in "TavilyResearch" shadows an attribute in parent "BaseTool"')
warnings.filterwarnings("ignore", message='Field name "stream" in "TavilyResearch" shadows an attribute in parent "BaseTool"')

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from contextlib import asynccontextmanager
import json
import asyncio
from logger_config import setup_logger

# Import the pipeline
from langchain_pipeline import (
    run_agent_pipeline, 
    stream_agent_response, 
    get_all_sessions, 
    get_session_state,
    clear_all_sessions,
    clear_session_context
)
from redis_client import redis_client

# Configure logging
logger = setup_logger("api")

# Global MongoDB client for reuse
mongodb_client = None

# ============================================================================
# Lifespan Event Handler
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown events
    """
    # Startup
    logger.info("🚀 LangChain Agentic Pipeline API starting up...")
    
    # Verify environment variables
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("⚠️ OPENAI_API_KEY not set!")
    
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("⚠️ TAVILY_API_KEY not set (web search will fail)")
    
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        logger.warning("⚠️ Langfuse keys not set (observability will be disabled)")
    else:
        logger.info("📊 Langfuse observability enabled")
        
    # Check Redis
    if redis_client.client:
        logger.info("✅ Redis connected")
    else:
        logger.warning("⚠️ Redis not connected (async queue will fail)")
    
    logger.info("✅ API ready to accept requests")
    
    yield
    
    # Shutdown
    logger.info("👋 LangChain Agentic Pipeline API shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Knowledge Bot API",
    description="Multi-agent LLM pipeline with streaming support",
    version="1.0.0",
    lifespan=lifespan
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only. In prod change to ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Request/Response Models
# ============================================================================

class ChatMessage(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class QueryRequest(BaseModel):
    """Request model for the pipeline"""
    query: str = Field(..., description="User's question or query", min_length=1)
    chat_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Previous conversation history"
    )
    session_id: Optional[str] = Field(
        default="default",
        description="Unique session ID for chat history persistence"
    )
    stream: Optional[bool] = Field(
        default=False,
        description="Enable streaming response"
    )
    model: Optional[str] = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use"
    )
    temperature: Optional[float] = Field(
        default=0.7,
        description="LLM temperature (0.0 to 1.0)"
    )
    target_language: Optional[str] = Field(
        default=None,
        description="Universal translation: if set, all answers will be translated to this language."
    )


class QueryResponse(BaseModel):
    """Response model for non-streaming queries"""
    success: bool
    query: str
    final_answer: str
    intent: Optional[str] = None
    routing_decision: Optional[str] = None
    citations: Optional[List[int]] = None
    error: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Request model for user feedback"""
    session_id: str = Field(..., description="Session ID")
    message_index: int = Field(..., description="Index of the message in the chat")
    feedback_type: str = Field(..., description="Feedback type: 'up' or 'down'")
    user_query: str = Field(..., description="Original user query")
    assistant_response: str = Field(..., description="Assistant's response")
    routing_decision: Optional[str] = Field(None, description="Routing decision made")
    intent: Optional[str] = Field(None, description="Detected intent")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    model_used: Optional[str] = Field("gpt-4o-mini", description="Model used for response")

    error: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def convert_chat_history(messages: List[ChatMessage]):
    """Convert API chat messages to LangChain messages"""
    if not messages:
        return []
    
    langchain_messages = []
    for msg in messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
    
    return langchain_messages


def get_llm(model: str, temperature: float) -> ChatOpenAI:
    """Initialize the LLM"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        streaming=True  # Enable streaming
    )


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "LangChain Agentic Pipeline",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check if OpenAI API key is configured
        api_key = os.getenv("OPENAI_API_KEY")
        openai_configured = bool(api_key)
        
        # Check if Tavily API key is configured (for web search)
        tavily_key = os.getenv("TAVILY_API_KEY")
        tavily_configured = bool(tavily_key)
        
        return {
            "status": "healthy",
            "openai_configured": openai_configured,
            "tavily_configured": tavily_configured,
            "endpoints": {
                "query": "/api/query",
                "stream": "/api/stream"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query", response_model=QueryResponse)
async def query_pipeline(request: QueryRequest):
    """
    Non-streaming query endpoint
    
    Executes the complete agentic pipeline and returns the final result.
    """
    try:
        logger.info(f"Received query: {request.query[:100]}...")
        
        # Initialize LLM
        llm = get_llm(request.model, request.temperature)
        
        # Convert chat history
        chat_history = convert_chat_history(request.chat_history or [])
        
        # Run the pipeline
        result = run_agent_pipeline(
            query=request.query,
            llm=llm,
            chat_history=chat_history,
            thread_id=request.session_id,
            stream=False,
            target_language=request.target_language
        )
        
        # Extract response data
        # Ensure final_answer is always a string, never None
        final_answer = result.get("final_answer") or "I apologize, but I couldn't generate an answer."
        
        response = QueryResponse(
            success=True,
            query=request.query,
            final_answer=final_answer,
            intent=result.get("intent"),
            routing_decision=str(result.get("routing_decision")) if result.get("routing_decision") else None,
            citations=result.get("citations"),
            error=result.get("error")
        )
        
        logger.info("Query completed successfully")
        return response
    
    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@app.post("/api/stream")
async def stream_query(request: QueryRequest):
    """
    Streaming query endpoint
    
    Streams the pipeline execution in real-time using Server-Sent Events (SSE).
    """
    try:
        logger.info(f"Received streaming query: {request.query[:100]}...")
        
        # Initialize LLM
        llm = get_llm(request.model, request.temperature)
        
        async def event_generator():
            """Generator for SSE events"""
            try:
                # Send initial event
                yield f"data: {json.dumps({'event': 'start', 'query': request.query})}\n\n"
                
                # Stream pipeline events
                async for event in stream_agent_response(
                    request.query, 
                    llm, 
                    thread_id=request.session_id,
                    target_language=request.target_language
                ):
                    event_data = json.dumps(event)
                    yield f"data: {event_data}\n\n"
                
                # Send completion event
                yield f"data: {json.dumps({'event': 'complete'})}\n\n"
            
            except Exception as e:
                logger.error(f"Streaming error: {str(e)}", exc_info=True)
                error_data = json.dumps({
                    'event': 'error',
                    'error': str(e)
                })
                yield f"data: {error_data}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable buffering in nginx
            }
        )
    
    except Exception as e:
        logger.error(f"Stream setup failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Stream setup failed: {str(e)}"
        )


@app.post("/api/queue")
async def queue_query(request: QueryRequest):
    """
    Async query endpoint (Redis Queue)
    
    Enqueues the query to be processed by a background worker.
    Returns a request_id immediately.
    """
    try:
        if not redis_client.client:
            raise HTTPException(status_code=503, detail="Redis service unavailable")
            
        job_data = {
            "query": request.query,
            "session_id": request.session_id,
            "model": request.model,
            "temperature": request.temperature,
            "target_language": request.target_language
        }
        
        request_id = redis_client.enqueue_job(job_data)
        
        return {
            "success": True, 
            "message": "Job enqueued", 
            "request_id": request_id,
            "stream_url": f"/api/stream/{request_id}"
        }
        
    except Exception as e:
        logger.error(f"Queue failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stream/{request_id}")
async def stream_job_results(request_id: str):
    """
    Subscribe to updates for a specific queued job via SSE.
    """
    try:
        if not redis_client.client:
            raise HTTPException(status_code=503, detail="Redis service unavailable")

        async def event_generator():
            pubsub = redis_client.get_pubsub()
            channel = f"job_updates:{request_id}"
            pubsub.subscribe(channel)
            
            try:
                # Yield initial connection message
                yield f"data: {json.dumps({'event': 'connected', 'request_id': request_id})}\n\n"
                
                # Listen for messages
                # We need to run the blocking listener in a way that yields
                while True:
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        data = message['data']
                        yield f"data: {data}\n\n"
                        
                        # Check for completion to close stream
                        try:
                            parsed = json.loads(data)
                            if parsed.get("event") in ["complete", "error"]:
                                break
                        except:
                            pass
                    else:
                        # Prevent tight loop spinning
                        await asyncio.sleep(0.1)
                        
            except Exception as e:
                logger.error(f"SSE loop error: {e}")
                yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"
            finally:
                pubsub.unsubscribe(channel)
                pubsub.close()
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
            
    except Exception as e:
        logger.error(f"Stream setup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/chat")
async def chat_endpoint(request: QueryRequest):
    """
    Chat endpoint with automatic streaming detection
    
    Returns streaming or non-streaming response based on request.stream flag.
    """
    if request.stream:
        return await stream_query(request)
    else:
        return await query_pipeline(request)


@app.get("/api/sessions")
async def list_sessions():
    """List all chat sessions from MongoDB"""
    try:
        sessions = get_all_sessions()
        return {"success": True, "sessions": sessions}
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return {"success": False, "error": str(e)}


@app.delete("/api/sessions")
async def delete_all_sessions():
    """Clear all chat sessions from MongoDB"""
    try:
        success = clear_all_sessions()
        if success:
            return {"success": True, "message": "All sessions cleared"}
        else:
            return {"success": False, "error": "Failed to clear sessions"}
    except Exception as e:
        logger.error(f"Failed to clear sessions: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get the state and history for a specific session"""
    try:
        state = get_session_state(session_id)
        if not state:
            return {"success": False, "error": "Session not found"}
        
        # Format history for the UI
        history = []
        raw_history = state.get("chat_history", [])
        
        for msg in raw_history:
            # Handle both LangChain message objects and dictionaries
            content = ""
            role = ""
            
            if hasattr(msg, 'content'):
                content = msg.content
                if isinstance(msg, HumanMessage):
                    role = "user"
                elif isinstance(msg, AIMessage):
                    role = "assistant"
                # Ignore ToolMessage, SystemMessage, etc.
            elif isinstance(msg, dict):
                content = msg.get('content', '')
                msg_type = msg.get('type') or msg.get('role')
                if msg_type in ['human', 'user']:
                    role = "user"
                elif msg_type in ['ai', 'assistant']:
                    role = "assistant"
            
            if content and role:
                history.append({"role": role, "content": content})
            
        return {
            "success": True, 
            "session_id": session_id,
            "summary": state.get("summary", ""),
            "history": history
        }
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        return {"success": False, "error": str(e)}


@app.delete("/api/sessions/{session_id}")
async def forget_session(session_id: str):
    """Clear/forget the context for a specific session (keeps session ID but resets history)"""
    try:
        success = clear_session_context(session_id)
        if success:
            return {
                "success": True, 
                "message": f"Context cleared for session '{session_id}'. You can continue with a fresh start."
            }
        else:
            return {"success": False, "error": "Failed to clear session context"}
    except Exception as e:
        logger.error(f"Failed to clear session {session_id}: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/feedback")
async def save_feedback(request: FeedbackRequest):
    """Save user feedback (thumbs up/down) for analytics and optimization"""
    try:
        mongo_url = os.getenv("MONGO_URL")
        if not mongo_url:
            logger.warning("MongoDB not configured, feedback not saved")
            return {"success": False, "error": "Database not configured"}
        
        # Connect to MongoDB
        global mongodb_client
        if mongodb_client is None:
            from pymongo import MongoClient
            mongodb_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        
        db = mongodb_client["agentic_pipeline"]
        feedback_collection = db["message_feedback"]
        
        # Create feedback document
        from datetime import datetime
        feedback_doc = {
            "session_id": request.session_id,
            "message_index": request.message_index,
            "timestamp": datetime.utcnow(),
            "user_query": request.user_query,
            "assistant_response": request.assistant_response,
            "routing_decision": request.routing_decision,
            "intent": request.intent,
            "feedback_type": request.feedback_type,
            "response_time_ms": request.response_time_ms,
            "model_used": request.model_used
        }
        
        # Insert into database
        result = feedback_collection.insert_one(feedback_doc)
        logger.info(f"📊 Feedback saved: {request.feedback_type} for session {request.session_id}, message {request.message_index}")
        
        return {
            "success": True,
            "feedback_id": str(result.inserted_id),
            "message": "Feedback saved successfully"
        }
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/analytics/feedback")
async def get_feedback_analytics(
    start_date: str = None,
    routing_decision: str = None,
    limit: int = 100
):
    """Get feedback analytics and insights"""
    try:
        mongo_url = os.getenv("MONGO_URL")
        if not mongo_url:
            return {"success": False, "error": "Database not configured"}
        
        global mongodb_client
        if mongodb_client is None:
            from pymongo import MongoClient
            mongodb_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        
        db = mongodb_client["agentic_pipeline"]
        feedback_collection = db["message_feedback"]
        
        # Build query filter
        query_filter = {}
        if start_date:
            from datetime import datetime
            query_filter["timestamp"] = {"$gte": datetime.fromisoformat(start_date)}
        if routing_decision:
            query_filter["routing_decision"] = routing_decision
        
        # Get overall statistics
        total_feedback = feedback_collection.count_documents(query_filter)
        thumbs_up = feedback_collection.count_documents({**query_filter, "feedback_type": "up"})
        thumbs_down = feedback_collection.count_documents({**query_filter, "feedback_type": "down"})
        
        satisfaction_rate = (thumbs_up / total_feedback * 100) if total_feedback > 0 else 0
        
        # Get statistics by routing decision
        pipeline = [
            {"$match": query_filter},
            {"$group": {
                "_id": "$routing_decision",
                "total": {"$sum": 1},
                "thumbs_up": {
                    "$sum": {"$cond": [{"$eq": ["$feedback_type", "up"]}, 1, 0]}
                },
                "thumbs_down": {
                    "$sum": {"$cond": [{"$eq": ["$feedback_type", "down"]}, 1, 0]}
                }
            }},
            {"$project": {
                "routing_decision": "$_id",
                "total": 1,
                "thumbs_up": 1,
                "thumbs_down": 1,
                "satisfaction_rate": {
                    "$multiply": [
                        {"$divide": ["$thumbs_up", "$total"]},
                        100
                    ]
                }
            }},
            {"$sort": {"satisfaction_rate": -1}}
        ]
        
        by_routing = list(feedback_collection.aggregate(pipeline))
        
        # Get recent feedback
        recent_feedback = list(
            feedback_collection.find(query_filter)
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        # Convert ObjectId to string for JSON serialization
        for item in recent_feedback:
            item["_id"] = str(item["_id"])
            item["timestamp"] = item["timestamp"].isoformat()
        
        logger.info(f"📊 Analytics retrieved: {total_feedback} total feedback entries")
        
        return {
            "success": True,
            "summary": {
                "total_feedback": total_feedback,
                "thumbs_up": thumbs_up,
                "thumbs_down": thumbs_down,
                "satisfaction_rate": round(satisfaction_rate, 2)
            },
            "by_routing_decision": by_routing,
            "recent_feedback": recent_feedback[:10]  # Return only 10 most recent
        }
    except Exception as e:
        logger.error(f"Analytics query failed: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# ============================================================================
# Run with: uvicorn api:app --reload --port 8000
# ============================================================================


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

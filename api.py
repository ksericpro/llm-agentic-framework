"""
FastAPI Application for LangChain Agentic Pipeline
Provides REST API endpoints with streaming support
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import json
import os
from dotenv import load_dotenv
import logging

# Import the pipeline
from langchain_pipeline import run_agent_pipeline, stream_agent_response

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LangChain Agentic Pipeline API",
    description="Multi-agent LLM pipeline with streaming support",
    version="1.0.0"
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
        description="Temperature for LLM",
        ge=0.0,
        le=2.0
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
            stream=False
        )
        
        # Extract response data
        final_answer = result.get("final_answer", "No answer generated")
        
        response = QueryResponse(
            success=True,
            query=request.query,
            final_answer=final_answer,
            intent=result.get("intent"),
            routing_decision=str(result.get("routing_decision")),
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
                async for event in stream_agent_response(request.query, llm):
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


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return {
        "success": False,
        "error": exc.detail,
        "status_code": exc.status_code
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return {
        "success": False,
        "error": "Internal server error",
        "detail": str(exc)
    }


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("🚀 LangChain Agentic Pipeline API starting up...")
    
    # Verify environment variables
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("⚠️ OPENAI_API_KEY not set!")
    
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("⚠️ TAVILY_API_KEY not set (web search will fail)")
    
    logger.info("✅ API ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("👋 LangChain Agentic Pipeline API shutting down...")


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

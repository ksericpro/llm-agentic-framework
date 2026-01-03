import asyncio
import os
import json
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load env vars
load_dotenv()

from redis_client import redis_client
from langchain_pipeline import stream_agent_response
from logger_config import setup_logger

logger = setup_logger("worker")

def get_llm(model: str, temperature: float):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        streaming=True
    )

async def process_job(job):
    request_id = job.get('request_id')
    query = job.get('query')
    model = job.get('model', 'gpt-4o-mini')
    temperature = job.get('temperature', 0.7)
    session_id = job.get('session_id', 'default')
    target_language = job.get('target_language')
    
    logger.info(f"Processing job {request_id}: {query[:50]}...")
    
    try:
        # Notify start
        redis_client.publish_update(request_id, {
            "event": "start", 
            "query": query,
            "request_id": request_id
        })
        
        llm = get_llm(model, temperature)
        
        # Run pipeline
        async for event in stream_agent_response(
            query=query, 
            llm=llm, 
            thread_id=session_id,
            target_language=target_language
        ):
            # Publish event
            redis_client.publish_update(request_id, event)
            
        # Notify completion
        redis_client.publish_update(request_id, {"event": "complete"})
        logger.info(f"Job {request_id} completed")
        
    except Exception as e:
        logger.error(f"Job {request_id} failed: {e}", exc_info=True)
        redis_client.publish_update(request_id, {
            "event": "error", 
            "error": str(e)
        })

async def main():
    logger.info("Worker started. Listening for jobs on 'agent_jobs'...")
    
    # Verify Redis connection
    if not redis_client.client:
        logger.error("❌ Redis not available. Exiting.")
        return

    while True:
        try:
            # Run blocking fetch in thread to avoid blocking the event loop
            job = await asyncio.to_thread(redis_client.fetch_job)
            
            if job:
                await process_job(job)
            else:
                # Small sleep not needed if fetch_job was blocking with timeout, 
                # but good safety if to_thread returns immediately for some reason
                await asyncio.sleep(0.01)
                
        except KeyboardInterrupt:
            logger.info("Worker stopping...")
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    #logger.info("Worker started. Listening for jobs on 'agent_jobs'...")
    asyncio.run(main())

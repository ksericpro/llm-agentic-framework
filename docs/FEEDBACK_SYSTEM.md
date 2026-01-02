# Feedback System: Implementation & Optimization Guide

## Overview

This guide explains how to store, analyze, and utilize user feedback (👍/👎) for continuous system improvement.

---

## 1. Database Schema

### Feedback Collection Table

```sql
CREATE TABLE message_feedback (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    message_index INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- User Input
    user_query TEXT NOT NULL,
    
    -- System Response
    assistant_response TEXT NOT NULL,
    routing_decision VARCHAR(50),
    intent VARCHAR(255),
    retrieved_context JSONB,
    
    -- Feedback
    feedback_type VARCHAR(10) CHECK (feedback_type IN ('up', 'down')),
    
    -- Metadata
    response_time_ms INTEGER,
    token_count INTEGER,
    model_used VARCHAR(50),
    
    -- Indexes
    INDEX idx_session (session_id),
    INDEX idx_feedback (feedback_type),
    INDEX idx_timestamp (timestamp),
    INDEX idx_routing (routing_decision)
);
```

### Analytics View

```sql
CREATE VIEW feedback_analytics AS
SELECT 
    DATE(timestamp) as date,
    routing_decision,
    COUNT(*) as total_responses,
    COUNT(CASE WHEN feedback_type = 'up' THEN 1 END) as thumbs_up,
    COUNT(CASE WHEN feedback_type = 'down' THEN 1 END) as thumbs_down,
    ROUND(AVG(CASE WHEN feedback_type = 'up' THEN 1 ELSE 0 END) * 100, 2) as satisfaction_rate,
    AVG(response_time_ms) as avg_response_time,
    AVG(token_count) as avg_tokens
FROM message_feedback
GROUP BY DATE(timestamp), routing_decision;
```

---

## 2. Backend Implementation

### Save Feedback Endpoint

```python
# Add to api.py

from datetime import datetime
from pymongo import MongoClient

@app.post("/api/feedback")
async def save_feedback(
    session_id: str,
    message_index: int,
    feedback_type: str,  # "up" or "down"
    query: str,
    response: str,
    routing_decision: str = None,
    intent: str = None,
    retrieved_context: list = None,
    response_time_ms: int = None,
    token_count: int = None,
    model_used: str = "gpt-4o-mini"
):
    """Store user feedback for analysis and optimization"""
    try:
        mongo_url = os.getenv("MONGO_URL")
        if not mongo_url:
            return {"success": False, "error": "Database not configured"}
        
        client = MongoClient(mongo_url)
        db = client["agentic_pipeline"]
        feedback_collection = db["message_feedback"]
        
        feedback_doc = {
            "session_id": session_id,
            "message_index": message_index,
            "timestamp": datetime.utcnow(),
            "user_query": query,
            "assistant_response": response,
            "routing_decision": routing_decision,
            "intent": intent,
            "retrieved_context": retrieved_context,
            "feedback_type": feedback_type,
            "response_time_ms": response_time_ms,
            "token_count": token_count,
            "model_used": model_used
        }
        
        result = feedback_collection.insert_one(feedback_doc)
        logger.info(f"📊 Feedback saved: {feedback_type} for session {session_id}")
        
        return {
            "success": True,
            "feedback_id": str(result.inserted_id)
        }
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        return {"success": False, "error": str(e)}
```

### Analytics Endpoint

```python
@app.get("/api/analytics/feedback")
async def get_feedback_analytics(
    start_date: str = None,
    end_date: str = None,
    routing_decision: str = None
):
    """Get feedback analytics and insights"""
    try:
        mongo_url = os.getenv("MONGO_URL")
        client = MongoClient(mongo_url)
        db = client["agentic_pipeline"]
        feedback_collection = db["message_feedback"]
        
        # Build query
        query = {}
        if start_date:
            query["timestamp"] = {"$gte": datetime.fromisoformat(start_date)}
        if routing_decision:
            query["routing_decision"] = routing_decision
        
        # Aggregate statistics
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": "$routing_decision",
                "total": {"$sum": 1},
                "thumbs_up": {
                    "$sum": {"$cond": [{"$eq": ["$feedback_type", "up"]}, 1, 0]}
                },
                "thumbs_down": {
                    "$sum": {"$cond": [{"$eq": ["$feedback_type", "down"]}, 1, 0]}
                },
                "avg_response_time": {"$avg": "$response_time_ms"},
                "avg_tokens": {"$avg": "$token_count"}
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
                },
                "avg_response_time": {"$round": ["$avg_response_time", 0]},
                "avg_tokens": {"$round": ["$avg_tokens", 0]}
            }}
        ]
        
        results = list(feedback_collection.aggregate(pipeline))
        
        return {
            "success": True,
            "analytics": results,
            "total_feedback": sum(r["total"] for r in results)
        }
    except Exception as e:
        logger.error(f"Analytics query failed: {e}")
        return {"success": False, "error": str(e)}
```

---

## 3. Frontend Integration

### Update UI to Send Feedback

```python
# Modify app.py feedback buttons

with col1:
    if st.button("👍", key=f"thumbs_up_{idx}", 
                help="Good response",
                type="primary" if current_feedback == "up" else "secondary"):
        st.session_state.feedback[msg_id] = "up"
        
        # Send to backend
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{API_BASE_URL}/api/feedback",
                    json={
                        "session_id": st.session_state.session_id,
                        "message_index": idx,
                        "feedback_type": "up",
                        "query": message.get("query", ""),
                        "response": message["content"],
                        "routing_decision": message.get("routing_decision"),
                        "intent": message.get("intent")
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to send feedback: {e}")
        
        st.toast("Thanks for your feedback! 👍", icon="✅")
        st.rerun()
```

---

## 4. Optimization Strategies

### A. Prompt Engineering

```python
# analyze_feedback.py

def analyze_low_rated_responses():
    """Find patterns in thumbs-down responses"""
    
    bad_responses = db.message_feedback.find({"feedback_type": "down"})
    
    patterns = {
        "routing_errors": [],
        "incomplete_answers": [],
        "factual_errors": [],
        "tone_issues": []
    }
    
    for response in bad_responses:
        # Analyze with LLM
        analysis = llm.invoke(f"""
        Analyze why this response might have received negative feedback:
        
        Query: {response['user_query']}
        Response: {response['assistant_response']}
        Routing: {response['routing_decision']}
        
        Categorize the issue: routing_error, incomplete, factual_error, or tone
        """)
        
        # Categorize
        if "routing" in analysis.lower():
            patterns["routing_errors"].append(response)
        # ... etc
    
    return patterns

# Use insights to improve prompts
def update_prompts_based_on_feedback():
    patterns = analyze_low_rated_responses()
    
    if len(patterns["routing_errors"]) > 10:
        print("⚠️ Routing issues detected. Consider adjusting router prompts.")
    
    if len(patterns["incomplete_answers"]) > 10:
        print("⚠️ Incomplete answers. Enhance generator prompts for completeness.")
```

### B. Fine-Tuning Dataset Creation

```python
# create_training_data.py

def export_training_data():
    """Export high-quality examples for fine-tuning"""
    
    # Get thumbs-up responses
    good_responses = db.message_feedback.find({
        "feedback_type": "up",
        "routing_decision": {"$exists": True}
    })
    
    training_examples = []
    
    for response in good_responses:
        example = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant..."
                },
                {
                    "role": "user",
                    "content": response["user_query"]
                },
                {
                    "role": "assistant",
                    "content": response["assistant_response"]
                }
            ]
        }
        training_examples.append(example)
    
    # Export to JSONL
    with open("training_data.jsonl", "w") as f:
        for example in training_examples:
            f.write(json.dumps(example) + "\n")
    
    print(f"✅ Exported {len(training_examples)} training examples")

# Fine-tune
def finetune_model():
    import openai
    
    # Upload training file
    with open("training_data.jsonl", "rb") as f:
        file_response = openai.File.create(
            file=f,
            purpose="fine-tune"
        )
    
    # Create fine-tuning job
    job = openai.FineTuningJob.create(
        training_file=file_response.id,
        model="gpt-4o-mini-2024-07-18",
        hyperparameters={
            "n_epochs": 3
        }
    )
    
    print(f"🚀 Fine-tuning job started: {job.id}")
```

### C. Routing Optimization

```python
# optimize_routing.py

def analyze_routing_accuracy():
    """Measure routing decision quality"""
    
    pipeline = [
        {"$group": {
            "_id": "$routing_decision",
            "total": {"$sum": 1},
            "thumbs_up": {
                "$sum": {"$cond": [{"$eq": ["$feedback_type", "up"]}, 1, 0]}
            }
        }},
        {"$project": {
            "routing_decision": "$_id",
            "total": 1,
            "accuracy": {
                "$multiply": [
                    {"$divide": ["$thumbs_up", "$total"]},
                    100
                ]
            }
        }},
        {"$sort": {"accuracy": 1}}  # Worst first
    ]
    
    results = list(db.message_feedback.aggregate(pipeline))
    
    print("📊 Routing Accuracy by Tool:")
    for result in results:
        tool = result["routing_decision"]
        accuracy = result["accuracy"]
        total = result["total"]
        
        print(f"  {tool}: {accuracy:.1f}% ({total} samples)")
        
        if accuracy < 70:
            print(f"    ⚠️ LOW ACCURACY - Review {tool} routing logic")

# Adjust routing thresholds based on feedback
def optimize_routing_thresholds():
    accuracy = analyze_routing_accuracy()
    
    # Example: If web_search has low accuracy, increase threshold
    if accuracy["web_search"] < 70:
        update_router_config({
            "web_search_threshold": 0.8  # Increase from 0.6
        })
```

### D. Retrieval Quality

```python
# optimize_retrieval.py

def analyze_retrieval_quality():
    """Find which retrieved documents lead to good responses"""
    
    good_retrievals = db.message_feedback.find({
        "feedback_type": "up",
        "retrieved_context": {"$exists": True, "$ne": []}
    })
    
    document_scores = {}
    
    for response in good_retrievals:
        for doc in response["retrieved_context"]:
            doc_id = doc.get("id") or doc.get("source")
            if doc_id:
                document_scores[doc_id] = document_scores.get(doc_id, 0) + 1
    
    # Sort by usefulness
    top_docs = sorted(document_scores.items(), key=lambda x: x[1], reverse=True)
    
    print("📚 Most Useful Documents:")
    for doc_id, count in top_docs[:10]:
        print(f"  {doc_id}: Used in {count} good responses")
    
    return top_docs
```

---

## 5. Automated Monitoring

### Dashboard Metrics

```python
# monitoring.py

def daily_feedback_report():
    """Generate daily feedback summary"""
    
    today = datetime.now().date()
    
    stats = db.message_feedback.aggregate([
        {"$match": {
            "timestamp": {
                "$gte": datetime.combine(today, datetime.min.time())
            }
        }},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "thumbs_up": {
                "$sum": {"$cond": [{"$eq": ["$feedback_type", "up"]}, 1, 0]}
            },
            "thumbs_down": {
                "$sum": {"$cond": [{"$eq": ["$feedback_type", "down"]}, 1, 0]}
            }
        }}
    ]).next()
    
    satisfaction_rate = (stats["thumbs_up"] / stats["total"]) * 100
    
    report = f"""
    📊 Daily Feedback Report - {today}
    
    Total Responses: {stats['total']}
    👍 Thumbs Up: {stats['thumbs_up']}
    👎 Thumbs Down: {stats['thumbs_down']}
    Satisfaction Rate: {satisfaction_rate:.1f}%
    
    {"✅ GOOD" if satisfaction_rate >= 80 else "⚠️ NEEDS ATTENTION"}
    """
    
    print(report)
    
    # Alert if satisfaction drops
    if satisfaction_rate < 70:
        send_alert("Low satisfaction rate detected!")
    
    return report
```

---

## 6. Long-term Improvements

### Continuous Learning Pipeline

```
1. Collect Feedback → MongoDB
2. Daily Analysis → Identify patterns
3. Weekly Review → Team discusses insights
4. Monthly Fine-tuning → Update models
5. Quarterly Evaluation → Measure improvement
```

### Metrics to Track

```python
metrics = {
    "satisfaction_rate": 85%,  # Target: >80%
    "response_quality_by_tool": {
        "web_search": 78%,
        "calculator": 95%,
        "internal_retrieval": 88%
    },
    "improvement_over_time": +5% per month,
    "cost_per_good_response": $0.02,
    "user_retention": 75%
}
```

---

## Summary

Feedback data enables:

✅ **Immediate**: Prompt engineering, routing fixes, quality monitoring  
✅ **Short-term**: A/B testing, retrieval optimization, edge case handling  
✅ **Long-term**: Model fine-tuning, RLHF, personalization  
✅ **Continuous**: Automated monitoring, degradation detection, trend analysis

The feedback loop creates a **self-improving system** that gets better over time! 🚀

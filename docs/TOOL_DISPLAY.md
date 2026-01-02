# Feature: Display Tool/Agent Used for Each Query

## ✅ Implemented

Added visual indicators showing which tool/agent was used to answer each query.

---

## 🎨 What You'll See

### During Query Processing (Streaming)
When the agent is thinking, you'll see in the status box:
```
🤖 Agent is thinking...
✅ Node: router_node completed
🌐 Tool Selected: web_search
✅ Node: retrieval_node completed
✅ Node: generator_node completed
✅ Task Complete!
```

### In Chat History
Each assistant message now shows:
```
🕒 15:53:09 | 📚 internal_retrieval

[Assistant's response here...]

👍 👎
```

---

## 🔧 Tool Icons

| Tool | Icon | Description |
|------|------|-------------|
| **web_search** | 🌐 | Web search using Tavily |
| **internal_retrieval** | 📚 | RAG from vector store (PDFs, docs) |
| **calculator** | 🔢 | Mathematical calculations |
| **targeted_crawl** | 🎯 | Targeted web crawling |
| **direct_answer** | 💬 | Direct LLM response (no tools) |
| **unknown** | 🔧 | Other/custom tools |

---

## 📊 Information Captured

For each assistant response, the system now stores:

```python
{
    "role": "assistant",
    "content": "The answer is...",
    "timestamp": "15:53:09",
    "routing_decision": "web_search",  # ← NEW!
    "intent": "information_request"    # ← NEW!
}
```

---

## 💡 Benefits

### 1. **Transparency**
Users can see exactly which tool was used to answer their question

### 2. **Debugging**
Quickly identify if the wrong tool was selected

### 3. **Analytics**
Track which tools are used most often (already integrated with feedback system!)

### 4. **Learning**
Users understand how the agentic system works

---

## 🎯 Example Scenarios

### Scenario 1: Calculator Query
```
User: "What is 15% of 1500?"

Status:
  🔢 Tool Selected: calculator

Response:
  🕒 15:53:09 | 🔢 calculator
  15% of 1500 is 225.
```

### Scenario 2: Web Search
```
User: "Latest news on SpaceX Starship"

Status:
  🌐 Tool Selected: web_search

Response:
  🕒 15:54:12 | 🌐 web_search
  According to recent reports, SpaceX Starship...
```

### Scenario 3: Internal Retrieval (RAG)
```
User: "What are the lessons in Rich Dad Poor Dad?"

Status:
  📚 Tool Selected: internal_retrieval

Response:
  🕒 15:55:30 | 📚 internal_retrieval
  Based on the book, the key lessons are...
```

---

## 🔍 How It Works

### Backend (Already Working)
The routing decision is already captured in `langchain_pipeline.py`:

```python
def router_node(state: AgentState) -> AgentState:
    router = RouterAgent(llm=state.get("llm"))
    decision = router.route(state["query"], ...)
    logger.info(f"✅ Routing decision: {decision.tool}")
    return {"routing_decision": decision}  # Stored in state
```

### Streaming (Already Working)
The decision is sent to the UI via streaming:

```python
yield {
    "node": node_name,
    "state": {
        "routing_decision": str(node_state.get("routing_decision")),
        "intent": node_state.get("intent"),
        ...
    }
}
```

### Frontend (NEW - Just Added)
1. **Capture during streaming**:
   - Parse routing decision from stream
   - Display in status box with icon

2. **Save with message**:
   - Store routing_decision and intent
   - Include in message metadata

3. **Display in chat**:
   - Show icon and tool name next to timestamp
   - Format: `🕒 15:53:09 | 🌐 web_search`

---

## 📁 Files Modified

| File | Changes |
|------|---------|
| `ui/app.py` | Added routing decision capture, display in status, badge in chat history |

---

## 🧪 Testing

1. **Restart the UI**:
   ```bash
   cd ui
   uv run streamlit run app.py
   ```

2. **Test different queries**:
   - **Calculator**: "What is 25% of 480?"
   - **Web Search**: "Latest AI news"
   - **Internal Retrieval**: "Lessons from Rich Dad Poor Dad"
   - **Direct Answer**: "What is machine learning?"

3. **Observe**:
   - Status box shows tool selection
   - Chat history shows tool badge
   - Feedback includes routing decision

---

## 📊 Integration with Feedback

The routing decision is now automatically included in feedback data:

```python
# When user clicks 👍 or 👎
feedback = {
    "session_id": "chat_123",
    "user_query": "What is AI?",
    "assistant_response": "AI is...",
    "routing_decision": "internal_retrieval",  # ← Automatically included!
    "intent": "information_request",
    "feedback_type": "up"
}
```

This enables analytics like:
- "Which tool has the highest satisfaction rate?"
- "Does web_search get more thumbs down than internal_retrieval?"
- "Should we improve calculator routing?"

---

## 🎨 Visual Example

```
┌─────────────────────────────────────────────────────┐
│ 👤 User                                             │
│ 🕒 15:53:09                                         │
│                                                     │
│ What are the lessons in Rich Dad Poor Dad?         │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 🤖 Assistant                                        │
│ 🕒 15:53:15 | 📚 internal_retrieval                │
│                                                     │
│ Based on the book "Rich Dad Poor Dad", the key     │
│ lessons include:                                    │
│ 1. The rich don't work for money...                │
│ 2. Financial literacy is crucial...                │
│                                                     │
│ 👍 👎                                               │
└─────────────────────────────────────────────────────┘
```

---

## 💡 Future Enhancements

Potential improvements:
- [ ] Click tool badge to see routing reasoning
- [ ] Filter chat history by tool used
- [ ] Show confidence score for routing decision
- [ ] Add tooltip explaining each tool
- [ ] Color-code tools (green=RAG, blue=web, etc.)

---

## Summary

✅ **Real-time display** - See tool selection as it happens  
✅ **Persistent badges** - Tool shown in chat history  
✅ **Icon-based** - Easy visual identification  
✅ **Analytics-ready** - Integrated with feedback system  
✅ **User-friendly** - Clear, non-technical display

Users can now see exactly which tool answered their question! 🎉

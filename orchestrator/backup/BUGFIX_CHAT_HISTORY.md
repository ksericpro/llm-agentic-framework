# Chat History Persistence Bug Fix

## Problem Description

When loading an old chat and continuing with new questions, then reloading the same chat, the old conversation was being replaced by the new messages instead of showing the complete history (both old and new messages combined).

## Root Cause

The issue was in the `stream_agent_response` function in `langchain_pipeline.py` (line 548). This function was hardcoding the `chat_history` to an empty list `[]` instead of loading the existing chat history from MongoDB.

```python
# BEFORE (Bug):
async def stream_agent_response(query: str, llm: ChatOpenAI, thread_id: str = "default"):
    app = create_agent_graph(llm)
    initial_state = {
        "query": query,
        "chat_history": [],  # ❌ Always starts with empty history!
        ...
    }
```

### What was happening:
1. User loads old chat → UI correctly displays old messages from MongoDB ✅
2. User sends new question → Backend starts with `chat_history: []` ❌
3. Backend processes new Q&A and saves to MongoDB with only the new messages
4. User reloads chat → Only sees the new messages (old ones were overwritten) ❌

## Solution

Modified `stream_agent_response` to load the existing chat history and summary from MongoDB before processing new queries:

```python
# AFTER (Fixed):
async def stream_agent_response(query: str, llm: ChatOpenAI, thread_id: str = "default"):
    app = create_agent_graph(llm)
    
    # Load existing chat history and summary from checkpointer if available
    existing_state = get_session_state(thread_id)
    existing_history = existing_state.get("chat_history", []) if existing_state else []
    existing_summary = existing_state.get("summary", "") if existing_state else ""
    
    initial_state = {
        "query": query,
        "chat_history": existing_history,  # ✅ Use existing history
        "llm": llm,
        ...
        "summary": existing_summary,  # ✅ Preserve existing summary
        ...
    }
```

### Now the flow works correctly:
1. User loads old chat → UI displays old messages ✅
2. User sends new question → Backend loads existing history from MongoDB ✅
3. Backend appends new Q&A to existing history and saves ✅
4. User reloads chat → Sees complete conversation (old + new) ✅

## Files Modified

1. **`langchain_pipeline.py`** (lines 545-569)
   - Updated `stream_agent_response` function to load existing chat history
   - Also loads existing summary to maintain complete conversation context

## Testing

Run the test script to verify the fix:

```bash
python test_history_persistence.py
```

The test will:
1. Create a new session
2. Send a first message
3. Verify the message is saved
4. Send a second message (continuing the conversation)
5. Reload the session and verify BOTH messages are present

Expected result: ✅ At least 4 messages (2 Q&A pairs) should be present in the history.

## Additional Notes

- The `run_agent_pipeline` function already had this correct (it accepts `chat_history` as a parameter)
- The bug only affected the streaming endpoint (`/api/stream`) used by the UI
- The fix also preserves the conversation summary, ensuring complete state continuity

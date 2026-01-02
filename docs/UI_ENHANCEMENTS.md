# UI Enhancements: Timestamps and Feedback

## Overview
Enhanced the Streamlit chat UI with timestamps for all messages and thumbs up/down feedback buttons for assistant responses.

## Features Added

### 1. **Timestamps for All Messages** ⏰
- **New messages**: Automatically timestamped with current time (HH:MM:SS format)
- **Loaded messages**: Display "Previously" for historical messages without specific timestamps
- **Consistent display**: All messages show a 🕒 timestamp caption

### 2. **Feedback Buttons for Assistant Responses** 👍👎
- **Thumbs up (👍)**: Mark good responses
- **Thumbs down (👎)**: Mark poor responses
- **Visual feedback**: Buttons highlight when selected (primary style)
- **Toast notifications**: Confirmation messages when feedback is submitted
- **Persistent state**: Feedback is stored in session state and persists during the session

## Implementation Details

### Session State Additions
```python
if "feedback" not in st.session_state:
    st.session_state.feedback = {}  # Store feedback for each message
```

### Message Display with Feedback
```python
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        # Display timestamp
        ts = message.get("timestamp", "")
        if ts:
            st.caption(f"🕒 {ts}")
        
        # Display message content
        st.markdown(message["content"])
        
        # Add feedback buttons for assistant messages
        if message["role"] == "assistant":
            col1, col2, col3 = st.columns([1, 1, 10])
            msg_id = f"msg_{idx}"
            current_feedback = st.session_state.feedback.get(msg_id, None)
            
            with col1:
                if st.button("👍", key=f"thumbs_up_{idx}", 
                            help="Good response",
                            type="primary" if current_feedback == "up" else "secondary"):
                    st.session_state.feedback[msg_id] = "up"
                    st.toast("Thanks for your feedback! 👍", icon="✅")
                    st.rerun()
            
            with col2:
                if st.button("👎", key=f"thumbs_down_{idx}", 
                            help="Poor response",
                            type="primary" if current_feedback == "down" else "secondary"):
                    st.session_state.feedback[msg_id] = "down"
                    st.toast("Thanks for your feedback. We'll improve! 👎", icon="📝")
                    st.rerun()
```

### Timestamp Handling for Loaded Messages
```python
# When loading chat history from API
loaded_messages = detail.get("history", [])
for msg in loaded_messages:
    if "timestamp" not in msg:
        msg["timestamp"] = "Previously"
st.session_state.messages = loaded_messages
```

## User Experience

### New Message Flow
1. User sends a message → Timestamped with current time (e.g., "14:30:45")
2. Assistant responds → Timestamped with current time
3. Assistant message displays with 👍 and 👎 buttons
4. User can click either button to provide feedback
5. Selected button highlights in primary color
6. Toast notification confirms feedback received

### Loading Old Chats
1. User loads previous conversation
2. All messages display with "Previously" timestamp
3. Feedback buttons appear for all assistant messages
4. User can provide feedback on historical responses

## Files Modified

1. **`ui/app.py`**
   - Added `feedback` to session state (line ~120)
   - Enhanced message display loop with timestamps and feedback buttons (lines ~207-237)
   - Added timestamp to new assistant responses (line ~285)
   - Added timestamp handling for loaded messages (lines ~152-157, ~179-184)

## Future Enhancements

Potential improvements for the feedback system:

1. **Backend Integration**: Send feedback to API for storage and analysis
   ```python
   # Example API endpoint
   POST /api/feedback
   {
       "session_id": "chat_123",
       "message_index": 2,
       "feedback": "up",  # or "down"
       "timestamp": "2026-01-02T15:00:00"
   }
   ```

2. **Feedback Analytics**: Track feedback metrics
   - Positive/negative ratio
   - Common issues in downvoted responses
   - Model performance over time

3. **Follow-up Actions**: When user clicks 👎
   - Show optional text input for detailed feedback
   - Offer to regenerate the response
   - Suggest alternative approaches

4. **Persistent Timestamps**: Store actual timestamps in MongoDB
   - Modify LangChain message storage to include metadata
   - Display exact time for historical messages

## Testing

To test the new features:

1. **Start the UI**:
   ```bash
   streamlit run ui/app.py
   ```

2. **Test timestamps**:
   - Send a new message → Should show current time
   - Load an old chat → Should show "Previously"

3. **Test feedback**:
   - Click 👍 on an assistant message → Button highlights, toast appears
   - Click 👎 on another message → Button highlights, toast appears
   - Reload the page → Feedback state resets (expected behavior)

## Notes

- Feedback is currently stored only in session state (not persisted to database)
- Timestamps for loaded messages show "Previously" as LangChain messages don't include timestamp metadata by default
- Feedback buttons use a 3-column layout to keep them compact and aligned to the left

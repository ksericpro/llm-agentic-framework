import streamlit as st
import os
import sys
import json
import time
import asyncio
import httpx
from typing import List, Dict, Any
import logging
from datetime import datetime, timedelta

# Add parent directory to path to import logger_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from logger_config import setup_logger
    logger = setup_logger("ui")
except ImportError:
    # Fallback if logger_config is not found
    logger = logging.getLogger("ui")
    logging.basicConfig(level=logging.INFO)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

def format_timestamp(ts_str):
    """Format ISO timestamp to a readable string"""
    if not ts_str:
        return ""
    try:
        # Handle various ISO formats
        ts_str = ts_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%b %d, %H:%M:%S")
    except Exception:
        # Fallback to simple string manipulation
        return ts_str[:19].replace('T', ' ')

def generate_new_session_id():
    return "chat_" + str(int(time.time()))

async def fetch_sessions(retries=2):
    """Fetch all sessions from the API with retry logic"""
    for i in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{API_BASE_URL}/api/sessions")
                if response.status_code == 200:
                    return response.json().get("sessions", [])
        except Exception as e:
            if i < retries:
                time.sleep(1) # Wait before retry
                continue
            st.error(f"Failed to connect to API at {API_BASE_URL}: {e}")
            if 'logger' in globals():
                logger.error(f"API Connection Error: {e}")
            else:
                print(f"API Connection Error: {e}")
    return []

async def fetch_session_detail(session_id: str):
    """Fetch detail for a specific session from the API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/sessions/{session_id}")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        st.error(f"Failed to fetch session detail: {e}")
    return None

def main():
    # Page configuration
    st.set_page_config(
        page_title="Agentic AI Dashboard",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for Premium Look
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
        }
        .stChatMessage {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 1rem;
            padding: 1rem;
        }
        .stSidebar {
            background-color: rgba(15, 23, 42, 0.95);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        .summary-card {
            background-color: rgba(59, 130, 246, 0.1);
            border-left: 4px solid #3b82f6;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }
        /* Sticky Header */
        div[data-testid="stVerticalBlock"] > div:has(div#sticky-header) {
            position: sticky;
            top: 2.875rem;
            background-color: #0f172a;
            z-index: 1000;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize Session State
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = generate_new_session_id()
    if "current_summary" not in st.session_state:
        st.session_state.current_summary = "No summary yet."
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None
    if "api_online" not in st.session_state:
        st.session_state.api_online = False
    if "feedback" not in st.session_state:
        st.session_state.feedback = {}  # Store feedback for each message
    if "target_language" not in st.session_state:
        st.session_state.target_language = "English"

    # Check API Health on first load
    if not st.session_state.api_online:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{API_BASE_URL}/health")
                if resp.status_code == 200:
                    st.session_state.api_online = True
        except Exception:
            st.warning("📡 Connecting to backend API...")
            time.sleep(1)
            st.rerun()

    # Sidebar
    with st.sidebar:
        st.title("🧠 Knowledge & History")
        
        st.session_state.target_language = st.selectbox(
            "🌍 Output Language",
            options=["English", "Chinese", "Spanish", "French", "German", "Japanese"],
            index=["English", "Chinese", "Spanish", "French", "German", "Japanese"].index(st.session_state.target_language),
            help="All agent responses will be translated to this language if not set to English."
        )
        st.divider()
        
        st.subheader("💡 Example Questions")
        
        # Mapping of short labels to full queries
        examples = {
            "💰 Financial Lessons (RDPD)": "What are the key financial lessons from Rich Dad Poor Dad?",
            "🎸 Guitar Gallery Inventory": "What acoustic guitars are featured on https://www.guitargallery.com.sg/ and what are their prices?",
            "🈯 Translate to Chinese": "Translate the following to Chinese: 'The quick brown fox jumps over the lazy dog'",
            "🔗 What is LangChain?": "What is LangChain?",
            "🤖 How do Agents work?": "How do agents work?",
        }
        
        for label, full_query in examples.items():
            # Use unique keys for example buttons to avoid conflicts
            if st.button(label, key=f"ex_{label}", use_container_width=True, help=full_query):
                st.session_state.pending_query = full_query
                st.rerun()

        st.divider()
        
        st.subheader("📂 Sessions History")
        show_all_sessions = st.checkbox("Show sessions older than 24h", value=False)
        
        sessions = asyncio.run(fetch_sessions())
        if sessions:
            # Filter sessions
            current_time = datetime.now()
            recent_sessions = []
            older_sessions = []
            
            for s in sessions:
                ts_str = s.get('last_updated')
                is_recent = False
                if ts_str:
                    try:
                        # Normalize Z suffix for fromisoformat
                        clean_ts = ts_str.replace('Z', '+00:00')
                        dt = datetime.fromisoformat(clean_ts)
                        # Check if within 24 hours (using naive comparison for simplicity if needed, 
                        # but let's try to be accurate with UTC if the API sends it)
                        if (current_time - dt.replace(tzinfo=None)) < timedelta(hours=24):
                            is_recent = True
                    except:
                        pass
                
                if is_recent:
                    recent_sessions.append(s)
                else:
                    older_sessions.append(s)
            
            display_list = recent_sessions if not show_all_sessions else sessions
            
            if not display_list:
                st.info("No recent sessions. Check 'Show older' to see more.")
            
            # Use a scrollable container for the session buttons
            with st.container(height=400):
                for s in display_list:
                    sid = s['session_id']
                    summary = s.get('summary') or "No summary available"
                    ts = format_timestamp(s.get('last_updated'))
                    
                    label = f"📄 {sid}\n🕒 {ts}"
                    if st.button(label, key=f"btn_{sid}", use_container_width=True, help=f"Summary: {summary}"):
                        st.session_state.session_id = sid
                        detail = asyncio.run(fetch_session_detail(sid))
                        if detail and detail.get("success"):
                            st.session_state.current_summary = detail.get("summary", "No summary yet.")
                            loaded_messages = detail.get("history", [])
                            for msg in loaded_messages:
                                if "timestamp" not in msg:
                                    msg["timestamp"] = "Previously"
                            st.session_state.messages = loaded_messages
                        st.rerun()
        else:
            st.info("No previous sessions found.")

        st.divider()
        
        st.subheader("📝 Conversation Summary")
        st.markdown(f'<div class="summary-card">{st.session_state.current_summary}</div>', unsafe_allow_html=True)

    # Main Chat Interface - Pinned Header
    with st.container():
        st.markdown('<div id="sticky-header"></div>', unsafe_allow_html=True)
        st.title("🚀 Agentic Pipeline")
        
        # Horizontal Settings Bar
        s_col1, s_col2, s_col3, s_col4 = st.columns([1.5, 1.5, 4, 2])
        
        with s_col1:
            if st.button("➕ New Chat", use_container_width=True, type="primary"):
                st.session_state.session_id = generate_new_session_id()
                st.session_state.messages = []
                st.session_state.current_summary = "No summary yet."
                st.rerun()
        
        with s_col2:
            if st.button("🧹 Forget", use_container_width=True, type="secondary"):
                try:
                    with httpx.Client(timeout=10.0) as client:
                        client.delete(f"{API_BASE_URL}/api/sessions/{st.session_state.session_id}")
                        st.session_state.messages = []
                        st.session_state.current_summary = "No summary yet."
                        st.toast("✅ Context cleared!", icon="🧹")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with s_col3:
            session_id_input = st.text_input("Session ID", value=st.session_state.session_id, label_visibility="collapsed")
            if session_id_input != st.session_state.session_id:
                st.session_state.session_id = session_id_input
                detail = asyncio.run(fetch_session_detail(st.session_state.session_id))
                if detail and detail.get("success"):
                    st.session_state.current_summary = detail.get("summary", "No summary yet.")
                    loaded_messages = detail.get("history", [])
                    for msg in loaded_messages:
                        if "timestamp" not in msg:
                            msg["timestamp"] = "Previously"
                    st.session_state.messages = loaded_messages
                st.rerun()
        
        with s_col4:
            msg_count = len(st.session_state.messages)
            color = "🔴" if msg_count >= 100 else "�" if msg_count >= 50 else "🟢"
            st.markdown(f"**{color} {msg_count} msgs**")
    
    # Warning for long conversations
    message_count = len(st.session_state.messages)
    if message_count >= 50:
        if message_count >= 100:
            st.warning(
                f"⚠️ **Very Long Conversation** ({message_count} messages)\n\n"
                "This conversation is getting very long. For optimal performance:\n"
                "- Click **🧹 Forget Context** to clear history and continue in this session\n"
                "- Click **➕ New Chat** to start fresh with a new session",
                icon="⚠️"
            )
        else:
            st.info(
                f"💡 **Long Conversation Notice** ({message_count} messages)\n\n"
                "Consider starting a new chat or clearing context for better performance.",
                icon="💡"
            )

    # Display chat messages
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            # Display timestamp and routing info
            ts = message.get("timestamp", "")
            routing_decision = message.get("routing_decision")
            
            if ts or routing_decision:
                caption_parts = []
                if ts:
                    caption_parts.append(f"🕒 {ts}")
                if routing_decision:
                    tool_icons = {
                        "web_search": "🌐",
                        "internal_retrieval": "📚",
                        "calculator": "🔢",
                        "targeted_crawl": "🎯",
                        "direct_answer": "💬"
                    }
                    icon = tool_icons.get(routing_decision, "🔧")
                    caption_parts.append(f"{icon} **{routing_decision}**")
                
                st.caption(" | ".join(caption_parts))
            
            # Display message content
            st.markdown(message["content"])
            
            # Add feedback buttons for assistant messages
            if message["role"] == "assistant":
                col1, col2, col3 = st.columns([0.5, 0.5, 11])
                msg_id = f"msg_{idx}"
                current_feedback = st.session_state.feedback.get(msg_id, None)
                
                with col1:
                    if st.button("👍", key=f"thumbs_up_{idx}", 
                                help="Good response",
                                type="primary" if current_feedback == "up" else "secondary"):
                        st.session_state.feedback[msg_id] = "up"
                        
                        # Send feedback to backend
                        try:
                            # Get the corresponding user message
                            user_query = ""
                            if idx > 0 and st.session_state.messages[idx-1]["role"] == "user":
                                user_query = st.session_state.messages[idx-1]["content"]
                            
                            with httpx.Client(timeout=10.0) as client:
                                response = client.post(
                                    f"{API_BASE_URL}/api/feedback",
                                    json={
                                        "session_id": st.session_state.session_id,
                                        "message_index": idx,
                                        "feedback_type": "up",
                                        "user_query": user_query,
                                        "assistant_response": message["content"],
                                        "routing_decision": message.get("routing_decision"),
                                        "intent": message.get("intent"),
                                        "model_used": "gpt-4o-mini"
                                    }
                                )
                                if response.status_code == 200:
                                    logger.info(f"✅ Feedback saved: thumbs up for message {idx}")
                        except Exception as e:
                            logger.warning(f"Failed to send feedback: {e}")
                        
                        st.toast("Thanks for your feedback! 👍", icon="✅")
                        st.rerun()
                
                with col2:
                    if st.button("👎", key=f"thumbs_down_{idx}", 
                                help="Poor response",
                                type="primary" if current_feedback == "down" else "secondary"):
                        st.session_state.feedback[msg_id] = "down"
                        
                        # Send feedback to backend
                        try:
                            # Get the corresponding user message
                            user_query = ""
                            if idx > 0 and st.session_state.messages[idx-1]["role"] == "user":
                                user_query = st.session_state.messages[idx-1]["content"]
                            
                            with httpx.Client(timeout=10.0) as client:
                                response = client.post(
                                    f"{API_BASE_URL}/api/feedback",
                                    json={
                                        "session_id": st.session_state.session_id,
                                        "message_index": idx,
                                        "feedback_type": "down",
                                        "user_query": user_query,
                                        "assistant_response": message["content"],
                                        "routing_decision": message.get("routing_decision"),
                                        "intent": message.get("intent"),
                                        "model_used": "gpt-4o-mini"
                                    }
                                )
                                if response.status_code == 200:
                                    logger.info(f"✅ Feedback saved: thumbs down for message {idx}")
                        except Exception as e:
                            logger.warning(f"Failed to send feedback: {e}")
                        
                        st.toast("Thanks for your feedback. We'll improve! 👎", icon="📝")
                        st.rerun()


    # Handle pending query
    query = None
    if st.session_state.pending_query:
        query = st.session_state.pending_query
        st.session_state.pending_query = None
    else:
        query = st.chat_input("Ask me anything... (Type /forget to clear context)")

    # Chat Input / Processing
    if query:
        # Check for special commands
        if query.strip().lower() in ["/forget", "/clear"]:
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.delete(f"{API_BASE_URL}/api/sessions/{st.session_state.session_id}")
                    if response.status_code == 200 and response.json().get("success"):
                        st.session_state.messages = []
                        st.session_state.current_summary = "No summary yet."
                        st.toast("✅ Context cleared! Starting fresh.", icon="🧹")
                        st.rerun()
                    else:
                        st.error("Failed to clear context")
            except Exception as e:
                st.error(f"Error clearing context: {e}")
            return  # Don't process as a normal query
        
        now = datetime.now().strftime("%H:%M:%S")
        st.session_state.messages.append({"role": "user", "content": query, "timestamp": now})
        with st.chat_message("user"):
            st.caption(f"🕒 {now}")
            st.markdown(query)


        # Agent Response via API Streaming
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            try:
                with st.status("🤖 Agent is thinking...", expanded=True) as status:
                    routing_info = {"tool": None, "intent": None}  # Track routing decision
                    
                    async def stream_from_api():
                        nonlocal full_response, routing_info
                        payload = {
                            "query": query,
                            "session_id": st.session_state.session_id,
                            "stream": True,
                            "target_language": st.session_state.target_language
                        }
                        
                        # Use httpx to stream the response from the API
                        async with httpx.AsyncClient(timeout=None) as client:
                            async with client.stream("POST", f"{API_BASE_URL}/api/stream", json=payload) as response:
                                if response.status_code != 200:
                                    st.error(f"API Error: {response.status_code}")
                                    return

                                async for line in response.aiter_lines():
                                    if line.startswith("data: "):
                                        data = json.loads(line[6:])
                                        
                                        # Handle different event types
                                        if data.get("event") == "start":
                                            continue
                                        elif data.get("event") == "complete":
                                            break
                                        elif data.get("event") == "error":
                                            st.error(f"Pipeline Error: {data.get('error')}")
                                            break
                                        
                                        # Handle node updates
                                        node = data.get("node")
                                        state = data.get("state", {})
                                        
                                        if node:
                                            status.write(f"✅ Node: **{node}** completed")
                                        
                                        # Capture routing decision
                                        if state.get("routing_decision") and state["routing_decision"] != "None":
                                            routing_str = str(state["routing_decision"])
                                            tool = None
                                            
                                            # Check if it's the simplified tool name
                                            valid_tools = ["web_search", "targeted_crawl", "internal_retrieval", "calculator"]
                                            if routing_str in valid_tools:
                                                tool = routing_str
                                            # Fallback for Pydantic-style string
                                            elif "tool=" in routing_str:
                                                try:
                                                    tool = routing_str.split("tool='")[1].split("'")[0]
                                                except:
                                                    pass
                                            
                                            if tool:
                                                routing_info["tool"] = tool
                                                # Show routing decision in status
                                                tool_icons = {
                                                    "web_search": "🌐",
                                                    "internal_retrieval": "📚",
                                                    "calculator": "🔢",
                                                    "targeted_crawl": "🕸️",
                                                    "translate": "🈯",
                                                    "direct_answer": "💬"
                                                }
                                                icon = tool_icons.get(tool, "🔧")
                                                status.write(f"{icon} **Tool Selected**: {tool}")
                                        
                                        # Capture intent
                                        if state.get("intent"):
                                            routing_info["intent"] = state["intent"]
                                        
                                        if state.get("summary"):
                                            st.session_state.current_summary = state["summary"]
                                        
                                        if state.get("final_answer"):
                                            full_response = state["final_answer"]
                                            response_placeholder.markdown(full_response)
                    
                    asyncio.run(stream_from_api())
                    status.update(label="✅ Task Complete!", state="complete", expanded=False)

                
                if not full_response:
                    full_response = "I processed your request but didn't generate a final text answer."
                    response_placeholder.markdown(full_response)
                    
                # Add timestamp to assistant response
                assistant_timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": full_response,
                    "timestamp": assistant_timestamp,
                    "routing_decision": routing_info.get("tool"),
                    "intent": routing_info.get("intent")
                })
                st.rerun()
                
            except Exception as e:
                st.error(f"Connection Error: {str(e)}")
                st.info("Make sure the backend API is running: `uv run api.py`")

if __name__ == "__main__":
    main()

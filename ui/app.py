import streamlit as st
import os
import sys
import json
import time
import asyncio
import httpx
from typing import List, Dict, Any

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def generate_new_session_id():
    return "chat_" + str(int(time.time()))

async def fetch_sessions():
    """Fetch all sessions from the API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/sessions")
            if response.status_code == 200:
                return response.json().get("sessions", [])
    except Exception as e:
        st.error(f"Failed to connect to API at {API_BASE_URL}. Is the server running?")
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

    # Sidebar
    with st.sidebar:
        st.title("🧠 Agent Settings")
        
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            st.session_state.session_id = generate_new_session_id()
            st.session_state.messages = []
            st.session_state.current_summary = "No summary yet."
            st.rerun()
            
        st.session_id_input = st.text_input("Current Session ID", value=st.session_state.session_id)
        if st.session_id_input != st.session_state.session_id:
            st.session_state.session_id = st.session_id_input
            # Load history via API
            detail = asyncio.run(fetch_session_detail(st.session_state.session_id))
            if detail and detail.get("success"):
                st.session_state.current_summary = detail.get("summary", "No summary yet.")
                st.session_state.messages = detail.get("history", [])
            else:
                st.session_state.messages = []
                st.session_state.current_summary = "No summary yet."
            st.rerun()

        st.divider()
        
        st.subheader("📂 Previous Sessions")
        sessions = asyncio.run(fetch_sessions())
        if sessions:
            for s in sessions[:10]:
                sid = s['session_id']
                summary = (s.get('summary') or "No summary")[:50] + "..."
                if st.button(f"📄 {sid}\n{summary}", key=f"btn_{sid}", use_container_width=True):
                    st.session_state.session_id = sid
                    detail = asyncio.run(fetch_session_detail(sid))
                    if detail and detail.get("success"):
                        st.session_state.current_summary = detail.get("summary", "No summary yet.")
                        st.session_state.messages = detail.get("history", [])
                    st.rerun()
        else:
            st.info("No previous sessions found or API offline.")

        st.divider()
        
        st.subheader("💡 Example Questions")
        examples = [
            "What is LangChain?",
            "How do agents work?",
            "Calculate 15% of 1500",
            "Search for the latest news on SpaceX Starship"
        ]
        
        for ex in examples:
            if st.button(ex, use_container_width=True):
                st.session_state.pending_query = ex
                st.rerun()
        
        st.divider()
        
        st.subheader("📝 Conversation Summary")
        st.markdown(f'<div class="summary-card">{st.session_state.current_summary}</div>', unsafe_allow_html=True)

    # Main Chat Interface
    st.title("🚀 Agentic Pipeline")
    st.caption(f"Session: {st.session_state.session_id} | Connected to: {API_BASE_URL}")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle pending query
    query = None
    if st.session_state.pending_query:
        query = st.session_state.pending_query
        st.session_state.pending_query = None
    else:
        query = st.chat_input("Ask me anything...")

    # Chat Input / Processing
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # Agent Response via API Streaming
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            try:
                with st.status("🤖 Agent is thinking...", expanded=True) as status:
                    async def stream_from_api():
                        nonlocal full_response
                        payload = {
                            "query": query,
                            "session_id": st.session_state.session_id,
                            "stream": True
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
                    
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                st.rerun()
                
            except Exception as e:
                st.error(f"Connection Error: {str(e)}")
                st.info("Make sure the backend API is running: `uv run api.py`")

if __name__ == "__main__":
    main()

# How to run
uv run streamlit run app.py

# Message Management

## Chat Length
1-49 msgs   → 🟢 Chat normally
50 msgs     → 💡 "Consider new chat" (can ignore)
100 msgs    → ⚠️ "Strongly recommend action" (can ignore)
150+ msgs   → ⚠️ Warning still shows (can still continue!)

## Message Summarization
Message 1-9:   No summary (not needed yet)
Message 10:    Summary created (messages 1-6 compressed)
Message 20:    Summary updated (messages 1-16 compressed)
Message 50:    Summary updated (messages 1-46 compressed)
Message 100:   Hierarchical summary (chunks → meta-summary)
Message 150:   Hierarchical summary updated
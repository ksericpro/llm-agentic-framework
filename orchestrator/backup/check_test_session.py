import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver

load_dotenv()

def check_test_session():
    mongo_url = os.getenv("MONGO_URL")
    client = MongoClient(mongo_url)
    saver = MongoDBSaver(client, db_name="checkpointing_db")
    
    config = {"configurable": {"thread_id": "test_session_123"}}
    state = saver.get(config)
    
    if state:
        print("Found state for test_session_123")
        if isinstance(state, dict):
            values = state.get('channel_values', {})
            history = values.get('chat_history', [])
            print(f"History length: {len(history)}")
            for i, msg in enumerate(history):
                print(f"Message {i}: type={type(msg)}, content={getattr(msg, 'content', 'N/A')}")
                if isinstance(msg, dict):
                    print(f"  Keys: {list(msg.keys())}")
                    print(f"  Data: {msg}")
    else:
        print("test_session_123 not found yet")

if __name__ == "__main__":
    check_test_session()

import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver

load_dotenv()

def check_history():
    mongo_url = os.getenv("MONGO_URL")
    client = MongoClient(mongo_url)
    saver = MongoDBSaver(client, db_name="checkpointing_db")
    
    config = {"configurable": {"thread_id": "test_session_999"}}
    state = saver.get(config)
    
    if state:
        print("Found state for test_session_999")
        # Based on previous debug, state is a dict
        values = state.get('channel_values', {})
        history = values.get('chat_history', [])
        print(f"History length: {len(history)}")
        for i, msg in enumerate(history):
            print(f"Message {i}: type={type(msg)}")
            # If it's a LangChain message object, it has a 'content' attribute
            # If it's a dict, it has a 'content' key
            if hasattr(msg, 'content'):
                print(f"  Content: {msg.content}")
            elif isinstance(msg, dict):
                print(f"  Content: {msg.get('content')}")
    else:
        print("test_session_999 not found")

if __name__ == "__main__":
    check_history()

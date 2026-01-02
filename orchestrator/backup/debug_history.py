import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

def debug_history():
    mongo_url = os.getenv("MONGO_URL")
    client = MongoClient(mongo_url)
    saver = MongoDBSaver(client, db_name="checkpointing_db")
    
    collection = client["checkpointing_db"]["checkpoints"]
    thread_ids = collection.distinct("thread_id")
    
    if thread_ids:
        tid = thread_ids[0]
        config = {"configurable": {"thread_id": tid}}
        state = saver.get(config)
        
        if isinstance(state, dict):
            values = state.get('channel_values', {})
            history = values.get('chat_history', [])
            print(f"Chat history length: {len(history)}")
            if history:
                msg = history[0]
                print(f"Message type: {type(msg)}")
                print(f"Message content: {getattr(msg, 'content', 'N/A')}")
                print(f"Is HumanMessage: {isinstance(msg, HumanMessage)}")
                print(f"Is AIMessage: {isinstance(msg, AIMessage)}")
                if isinstance(msg, dict):
                    print(f"Message keys: {list(msg.keys())}")

if __name__ == "__main__":
    debug_history()

import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver

load_dotenv()

def find_history():
    mongo_url = os.getenv("MONGO_URL")
    client = MongoClient(mongo_url)
    saver = MongoDBSaver(client, db_name="checkpointing_db")
    
    collection = client["checkpointing_db"]["checkpoints"]
    thread_ids = collection.distinct("thread_id")
    
    for tid in thread_ids:
        config = {"configurable": {"thread_id": tid}}
        state = saver.get(config)
        if isinstance(state, dict):
            values = state.get('channel_values', {})
            history = values.get('chat_history', [])
            if history:
                print(f"Found history for thread_id: {tid}, length: {len(history)}")
                msg = history[0]
                print(f"  Type: {type(msg)}")
                return
    print("No sessions with history found")

if __name__ == "__main__":
    find_history()

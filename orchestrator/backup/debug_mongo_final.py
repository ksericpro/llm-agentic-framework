import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver

load_dotenv()

def debug_mongodb():
    mongo_url = os.getenv("MONGO_URL")
    client = MongoClient(mongo_url)
    saver = MongoDBSaver(client, db_name="checkpointing_db")
    
    collection = client["checkpointing_db"]["checkpoints"]
    thread_ids = collection.distinct("thread_id")
    
    if thread_ids:
        tid = thread_ids[0]
        config = {"configurable": {"thread_id": tid}}
        state = saver.get(config)
        
        print(f"State type: {type(state)}")
        if isinstance(state, dict):
            print(f"State keys: {list(state.keys())}")
            if 'checkpoint' in state:
                print("State has 'checkpoint' key")
            if 'channel_values' in state:
                print("State has 'channel_values' key")
        else:
            print(f"State attributes: {dir(state)}")
            if hasattr(state, 'checkpoint'):
                print("State has 'checkpoint' attribute")
                if isinstance(state.checkpoint, dict):
                    print(f"Checkpoint keys: {list(state.checkpoint.keys())}")

if __name__ == "__main__":
    debug_mongodb()

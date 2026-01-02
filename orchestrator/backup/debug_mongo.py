import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver
import pickle

load_dotenv()

def debug_mongodb():
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        print("MONGO_URL not found")
        return

    client = MongoClient(mongo_url)
    db = client["checkpointing_db"]
    collection = db["checkpoints"]
    
    print(f"Total documents in checkpoints collection: {collection.count_documents({})}")
    
    sample = collection.find_one()
    if sample:
        print("\n--- Raw MongoDB Document Keys ---")
        for k, v in sample.items():
            print(f"Key: {k}, Type: {type(v)}")
            if k == 'checkpoint' and isinstance(v, bytes):
                try:
                    # Try to unpickle to see what's inside
                    data = pickle.loads(v)
                    print(f"  Decoded checkpoint type: {type(data)}")
                    if isinstance(data, dict):
                        print(f"  Decoded checkpoint keys: {list(data.keys())}")
                        if 'ts' in data:
                            print(f"    ts: {data['ts']}")
                except:
                    print("  Could not decode checkpoint as pickle")

    # Test MongoDBSaver.get
    print("\n--- Testing MongoDBSaver.get ---")
    saver = MongoDBSaver(client, db_name="checkpointing_db")
    thread_ids = collection.distinct("thread_id")
    if thread_ids:
        tid = thread_ids[0]
        print(f"Testing for thread_id: {tid}")
        config = {"configurable": {"thread_id": tid}}
        try:
            state = saver.get(config)
            print(f"Returned state type: {type(state)}")
            
            # Check if it's a CheckpointTuple (standard for LangGraph 0.2+)
            # CheckpointTuple has: config, checkpoint, metadata, parent_config
            if hasattr(state, 'checkpoint'):
                print("State has 'checkpoint' attribute")
                cp = state.checkpoint
                print(f"  Checkpoint type: {type(cp)}")
                if isinstance(cp, dict):
                    print(f"  Checkpoint keys: {list(cp.keys())}")
                    if 'channel_values' in cp:
                        print(f"  Channel values keys: {list(cp['channel_values'].keys())}")
            
            if hasattr(state, 'metadata'):
                print(f"State has 'metadata' attribute: {state.metadata}")
                
            if isinstance(state, dict):
                print("State is a dict. Keys:", list(state.keys()))
                
        except Exception as e:
            print(f"Error during saver.get: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("No thread_ids found")

if __name__ == "__main__":
    debug_mongodb()

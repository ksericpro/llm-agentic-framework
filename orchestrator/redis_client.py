import os
import redis
import json
import uuid
import logging

# Configure logger
logger = logging.getLogger("redis_client")

# Default Redis URL
DEFAULT_REDIS_URL = "redis://localhost:6379/0"

class RedisClient:
    def __init__(self, url=None):
        self.url = url or os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
        self.client = None
        self.connect()

    def connect(self):
        try:
            self.client = redis.from_url(self.url, decode_responses=True)
            self.client.ping()
            logger.info(f"✅ Connected to Redis at {self.url}")
        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Could not connect to Redis at {self.url}: {e}")
            self.client = None

    def enqueue_job(self, job_data):
        """
        Push a job to the queue. 
        Returns the generated request_id.
        """
        if not self.client:
            raise Exception("Redis client not connected")
        
        request_id = str(uuid.uuid4())
        job_data['request_id'] = request_id
        job_data['status'] = 'queued'
        
        # We use a simple list as a queue
        self.client.rpush('agent_jobs', json.dumps(job_data))
        logger.info(f"Job {request_id} enqueued")
        
        return request_id

    def publish_update(self, request_id, data):
        """
        Publish an update for a specific request ID.
        """
        if not self.client:
            return
            
        channel = f"job_updates:{request_id}"
        self.client.publish(channel, json.dumps(data))

    def get_pubsub(self):
        """
        Get a pubsub object to subscribe to channels.
        """
        if not self.client:
            raise Exception("Redis client not connected")
        return self.client.pubsub()

    def fetch_job(self):
        """
        Blocking pop a job from the queue.
        """
        if not self.client:
            return None
            
        # blpop returns (key, value) tuple
        result = self.client.blpop('agent_jobs', timeout=1)
        if result:
            return json.loads(result[1])
        return None

# Singleton instance
redis_client = RedisClient()

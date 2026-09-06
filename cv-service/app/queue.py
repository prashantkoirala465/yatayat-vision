import redis
from rq import Queue

from app.config import settings

redis_conn = redis.from_url(settings.redis_url)
video_queue = Queue("video_processing", connection=redis_conn)

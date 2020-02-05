import redis

from everyclass.server.config import get_config

config = get_config()
redis = redis.Redis(**config.REDIS)

redis_prefix = "ec_sv"

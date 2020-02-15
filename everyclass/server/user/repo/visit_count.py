from flask import session

from everyclass.server.db.redis import redis, redis_prefix
from everyclass.server.models import UserSession


def add_visitor_count(sid_orig: str, visitor: UserSession = None) -> None:
    """增加用户的总访问人数"""
    if not visitor:  # 未登录用户使用分配的user_id代替学号标识
        visitor_sid_orig = "anm" + str(session["user_id"])
    else:
        if sid_orig != visitor.identifier:  # 排除自己的访问量
            return
        visitor_sid_orig = visitor.identifier
    redis.pfadd("{}:visit_cnt:{}".format(redis_prefix, sid_orig), visitor_sid_orig)


def get_visitor_count(sid_orig: str) -> int:
    """获得总访问人数计数"""
    return redis.pfcount("{}:visit_cnt:{}".format(redis_prefix, sid_orig))

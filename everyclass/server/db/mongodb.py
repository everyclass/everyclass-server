from flask import current_app, has_app_context
from pymongo import MongoClient

from everyclass.server.config import get_config


def init_pool(current_application) -> None:
    """创建连接池，保存在 app 的 mongo_pool 对象中"""
    current_application.mongo = MongoClient(**current_application.config['MONGODB'])


def get_connection() -> MongoClient:
    """在连接池中获得连接"""
    if not has_app_context():
        config = get_config()
        return MongoClient(**config.MONGODB)[config.MONGODB_DB]
    return current_app.mongo[current_app.config['MONGODB_DB']]

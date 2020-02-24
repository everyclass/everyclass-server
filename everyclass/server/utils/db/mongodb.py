from flask import current_app, has_app_context
from pymongo import MongoClient, database

from everyclass.server.utils.config import get_config


def init_pool(current_application) -> None:
    """创建连接池，保存在 app 的 mongo 属性中"""
    current_application.mongo = MongoClient(**current_application.config['MONGODB'])


def get_connection() -> database.Database:
    """在连接池中获得连接"""
    if not has_app_context():
        config = get_config()
        return MongoClient(**config.MONGODB).get_database(config.MONGODB_DB)
    return current_app.mongo.get_database(current_app.config['MONGODB_DB'])

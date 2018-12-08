"""
MySQL 数据库有关操作
"""

import pymysql
from DBUtils.PooledDB import PooledDB
from flask import current_app as app


def init_pool(current_app):
    """创建连接池，保存在 app 的 mysql_pool 对象中"""
    current_app.mysql_pool = PooledDB(creator=pymysql, **current_app.config['MYSQL_CONFIG'])


def get_connection():
    """在连接池中获得连接"""
    return app.mysql_pool.connection()

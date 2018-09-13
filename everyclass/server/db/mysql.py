"""
数据库有关操作
"""

from flask import current_app as app, g

from everyclass.server.db import pool


def get_connection():
    """获得单个 Connection"""
    import pymysql
    from everyclass.server.config import get_config
    config = get_config()
    return pymysql.Connection(config['MYSQL_CONFIG'])


def init_pool(current_app):
    """创建连接池，保存在 app 的 mysql_pool 对象中"""
    current_app.mysql_pool = pool.ConnectionPool(**current_app.config['MYSQL_CONFIG'])


def get_local_conn():
    """获取每个线程的数据库连接，如当前线程 g 变量中没有 mysql_db，在连接池中获得连接并保存引用到当前线程"""
    if not hasattr(g, 'mysql_db'):
        g.mysql_db = app.mysql_pool.get_connection()
    return g.mysql_db

"""
数据库有关操作
"""

from flask import current_app as app
from flask import g, app

from everyclass.db import pool


def init_db(current_app: app):
    """创建连接池"""
    current_app.mysql_pool = pool.ConnectionPool(**current_app.config['MYSQL_CONFIG'])


def get_conn():
    """获取每个线程的数据库连接，如当前线程 g 变量中没有 mysql_db，在连接池中获得连接并保存引用到当前线程"""
    if not hasattr(g, 'mysql_db'):
        g.mysql_db = app.mysql_pool.get_connection()
    return g.mysql_db

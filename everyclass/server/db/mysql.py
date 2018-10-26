"""
MySQL 数据库有关操作
"""

import pymysql
from DBUtils.PooledDB import PooledDB
from flask import current_app as app


def init_pool(current_app):
    """创建连接池，保存在 app 的 mysql_pool 对象中"""
    # current_app.mysql_pool = pool.ConnectionPool(**current_app.config['MYSQL_CONFIG'])
    current_app.mysql_pool = PooledDB(creator=pymysql,
                                      mincached=1,
                                      maxcached=5,
                                      maxconnections=100,
                                      host=current_app.config['MYSQL_CONFIG']['host'],
                                      user=current_app.config['MYSQL_CONFIG']['user'],
                                      passwd=current_app.config['MYSQL_CONFIG']['password'],
                                      db=current_app.config['MYSQL_CONFIG']['database'],
                                      port=current_app.config['MYSQL_CONFIG']['port'],
                                      charset=current_app.config['MYSQL_CONFIG']['charset'])


def get_connection():
    """在连接池中获得连接"""
    return app.mysql_pool.connection()

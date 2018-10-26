"""
MySQL 数据库有关操作
"""

import pymysql
from DBUtils.PooledDB import PooledDB
from flask import current_app as app, g


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


def get_local_conn():
    """获取每个线程的数据库连接，如当前线程 g 变量中没有 mysql_db，在连接池中获得连接并保存引用到当前线程"""
    if not hasattr(g, 'mysql_db'):
        g.mysql_db = app.mysql_pool.connection()
    return g.mysql_db

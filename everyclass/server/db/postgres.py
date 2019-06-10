from contextlib import contextmanager

import psycopg2
from DBUtils.PooledDB import PooledDB
from flask import current_app, has_app_context
from psycopg2.extras import register_hstore, register_uuid

from everyclass.server.config import get_config

_config = get_config()
_options = f'-c search_path={_config.POSTGRES_SCHEMA}'


def init_pool(current_application) -> None:
    """创建连接池，保存在 app 的 postgres 属性中"""
    # more information at https://cito.github.io/DBUtils/UsersGuide.html
    current_application.postgres = PooledDB(creator=psycopg2,
                                            mincached=1,
                                            maxcached=4,
                                            maxconnections=4,
                                            blocking=True,
                                            **_config.POSTGRES_CONNECTION,
                                            options=_options)


@contextmanager
def pg_conn_context():
    if has_app_context():
        conn = current_app.postgres.connection()
    else:
        conn = psycopg2.connect(**_config.POSTGRES_CONNECTION,
                                options=_options)
    register_types(conn)
    yield conn
    conn.close()


def register_types(conn):
    if has_app_context():
        real_conn = conn._con._con
        # conn 是 PooledDB（或PersistentDB）的连接，它的 _con 是 SteadyDB。而 SteadyDB 的 _con 是原始的 psycopg2 连接对象
    else:
        real_conn = conn
    register_uuid(conn_or_curs=real_conn)
    register_hstore(conn_or_curs=real_conn)

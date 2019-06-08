from contextlib import contextmanager

import psycopg2
import psycopg2.extensions
import psycopg2.pool
from flask import current_app, has_app_context

from everyclass.server.config import get_config

_config = get_config()
_options = f'-c search_path={_config.POSTGRES_SCHEMA}'


def init_pool(current_application) -> None:
    """创建连接池，保存在 app 的 postgres 属性中"""
    current_application.postgres = psycopg2.pool.ThreadedConnectionPool(1, 10,
                                                                        **_config.POSTGRES_CONNECTION,
                                                                        options=_options)


@contextmanager
def pg_conn_context():
    if has_app_context():
        conn = current_app.postgres.getconn()
    else:
        conn = psycopg2.connect(**_config.POSTGRES_CONNECTION,
                                options=_options)
    yield conn
    put_pg_conn(conn)


def put_pg_conn(conn) -> None:
    """将连接放回连接池"""
    if has_app_context():
        current_app.postgres.putconn(conn)
    else:
        conn.close()

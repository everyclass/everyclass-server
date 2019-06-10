from contextlib import contextmanager

import psycopg2
from DBUtils.PooledDB import PooledDB
from flask import current_app, has_app_context

from everyclass.server.config import get_config

_config = get_config()
_options = f'-c search_path={_config.POSTGRES_SCHEMA}'


def init_pool(current_application) -> None:
    """创建连接池，保存在 app 的 postgres 属性中"""
    current_application.postgres = PooledDB(creator=psycopg2,
                                            mincached=1,
                                            maxcached=3,
                                            maxconnections=10,
                                            **_config.POSTGRES_CONNECTION,
                                            options=_options)


@contextmanager
def pg_conn_context():
    if has_app_context():
        conn = current_app.postgres.connection()
    else:
        conn = psycopg2.connect(**_config.POSTGRES_CONNECTION,
                                options=_options)
    yield conn
    conn.close()

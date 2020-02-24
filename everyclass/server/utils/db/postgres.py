from contextlib import contextmanager

from everyclass.server.utils.config import get_config

_config = get_config()


def init_pool() -> None:
    """创建连接池"""
    from everyclass.common.postgres import init_pool as init
    init(_config.POSTGRES_SCHEMA, _config.POSTGRES_CONNECTION)


@contextmanager
def pg_conn_context():
    from everyclass.common.postgres import conn_context_with_retry as context
    with context() as conn:
        yield conn

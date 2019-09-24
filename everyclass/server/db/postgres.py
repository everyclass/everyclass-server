from contextlib import contextmanager

from everyclass.server.config import get_config

_config = get_config()


def init_pool() -> None:
    """创建连接池"""
    from everyclass.common.postgres import init_pool as init
    init(_config.POSTGRES_SCHEMA, _config.POSTGRES_CONNECTION)


@contextmanager
def pg_conn_context():
    from everyclass.common.postgres import conn_context as context
    success = False

    try:
        with context as conn:
            yield conn
    except RuntimeError:
        # 连接池没有被初始化
        pass
    else:
        success = True

    if not success:
        # 没有成功说明连接池没有被初始化，先初始化再调用
        init_pool()
        with context as conn:
            yield conn

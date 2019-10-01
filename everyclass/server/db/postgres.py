from contextlib import contextmanager

from everyclass.server.config import get_config

_config = get_config()


def init_pool() -> None:
    """创建连接池"""
    from everyclass.common.postgres import init_pool as init
    init(_config.POSTGRES_SCHEMA, _config.POSTGRES_CONNECTION)


MAX_TRIALS = 2


@contextmanager
def pg_conn_context():
    from everyclass.common.postgres import conn_context as context
    success = False
    trials = 0

    while not success and trials < MAX_TRIALS:
        try:
            with context() as conn:
                yield conn
        except RuntimeError:
            # 连接池没有被初始化
            init_pool()
        else:
            success = True
        finally:
            trials += 1
    if not success:
        raise RuntimeError(f"DB connection context failed after {trials} trials")

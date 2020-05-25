from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from everyclass.server.utils.config import get_config

_config = get_config()
_conn_config = _config.POSTGRES_CONNECTION
_engine = create_engine(
    f'postgresql+psycopg2://{_conn_config["user"]}:{_conn_config["password"]}@{_conn_config["host"]}:{_conn_config["port"]}/{_conn_config["dbname"]}',
    connect_args={'options': f'-c search_path={_config.POSTGRES_SCHEMA}'},
    echo=True)
db_session = scoped_session(sessionmaker(bind=_engine))
Base = declarative_base()


def register_model_to_base():
    import everyclass.server.calendar.model
    import everyclass.server.course.model
    import everyclass.server.entity.model
    import everyclass.server.user.model
    _ = everyclass.server.calendar.model
    _ = everyclass.server.course.model
    _ = everyclass.server.entity.model
    _ = everyclass.server.user.model


def create_table():
    """建表"""
    register_model_to_base()
    Base.metadata.create_all(_engine)


def init_pool() -> None:
    """创建连接池。仅在fork后运行一次，否则连接可能中断。"""
    from everyclass.common.postgres import init_pool as init
    init(_config.POSTGRES_SCHEMA, _config.POSTGRES_CONNECTION)

    _engine.dispose()


@contextmanager
def pg_conn_context():
    from everyclass.common.postgres import conn_context_with_retry as context
    with context() as conn:
        yield conn

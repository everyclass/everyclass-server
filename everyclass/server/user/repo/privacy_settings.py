import datetime

from everyclass.server.utils.config import get_config
from everyclass.server.utils.db import pg_conn_context


def get_level(student_id: str) -> int:
    with pg_conn_context() as conn, conn.cursor() as cursor:
        select_query = "SELECT level FROM privacy_settings WHERE student_id=%s"
        cursor.execute(select_query, (student_id,))
        result = cursor.fetchone()
    return result[0] if result is not None else get_config().DEFAULT_PRIVACY_LEVEL


def set_level(student_id: str, new_level: int) -> None:
    with pg_conn_context() as conn, conn.cursor() as cursor:
        insert_query = """
        INSERT INTO privacy_settings (student_id, level, create_time) VALUES (%s,%s,%s)
            ON CONFLICT (student_id) DO UPDATE SET level=EXCLUDED.level
        """
        cursor.execute(insert_query, (student_id, new_level, datetime.datetime.now()))
        conn.commit()

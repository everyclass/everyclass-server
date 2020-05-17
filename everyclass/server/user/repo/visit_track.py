import datetime
from typing import List, Tuple

from everyclass.server.utils.db import pg_conn_context


def update_track(host: str, visitor: str) -> None:
    with pg_conn_context() as conn, conn.cursor() as cursor:
        insert_or_update_query = """
        INSERT INTO visit_tracks (host_id, visitor_id, last_visit_time) VALUES (%s,%s,%s)
            ON CONFLICT ON CONSTRAINT unq_host_visitor DO UPDATE SET last_visit_time=EXCLUDED.last_visit_time;
        """
        cursor.execute(insert_or_update_query, (host, visitor, datetime.datetime.now()))
        conn.commit()


def get_visitors(identifier: str) -> List[Tuple[str, int]]:
    """获得学生访客列表，包含访客的学号或教工号及访问时间"""
    with pg_conn_context() as conn, conn.cursor() as cursor:
        select_query = """
        SELECT visitor_id, last_visit_time FROM visit_tracks where host_id=%s ORDER BY last_visit_time DESC;
        """
        cursor.execute(select_query, (identifier,))
        result = cursor.fetchall()
        conn.commit()
    return result

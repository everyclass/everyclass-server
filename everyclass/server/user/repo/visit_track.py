import datetime
from typing import List

from everyclass.server.db.postgres import pg_conn_context
from everyclass.server.user.entity import Visitor
from everyclass.server.utils.session import USER_TYPE_TEACHER, USER_TYPE_STUDENT


def update_track(host: str, visitor: str) -> None:
    with pg_conn_context() as conn, conn.cursor() as cursor:
        insert_or_update_query = """
        INSERT INTO visit_tracks (host_id, visitor_id, last_visit_time) VALUES (%s,%s,%s)
            ON CONFLICT ON CONSTRAINT unq_host_visitor DO UPDATE SET last_visit_time=EXCLUDED.last_visit_time;
        """
        cursor.execute(insert_or_update_query, (host, visitor, datetime.datetime.now()))
        conn.commit()


def get_visitors(identifier: str) -> List[Visitor]:
    """获得访客列表"""
    from everyclass.rpc.entity import Entity

    with pg_conn_context() as conn, conn.cursor() as cursor:
        select_query = """
        SELECT visitor_id, last_visit_time FROM visit_tracks where host_id=%s ORDER BY last_visit_time DESC;
        """
        cursor.execute(select_query, (identifier,))
        result = cursor.fetchall()
        conn.commit()

    visitor_list = []
    for record in result:
        # query entity
        # todo: entity add a multi GET interface to make this process faster when the list is long
        search_result = Entity.search(record[0])
        if len(search_result.students) > 0:
            visitor_list.append(Visitor(name=search_result.students[0].name,
                                        user_type=USER_TYPE_STUDENT,
                                        identifier_encoded=search_result.students[0].student_id_encoded,
                                        last_semester=search_result.students[0].semesters[-1],
                                        visit_time=record[1]))
        elif len(search_result.teachers) > 0:
            visitor_list.append(Visitor(name=search_result.teachers[0].name,
                                        user_type=USER_TYPE_TEACHER,
                                        identifier_encoded=search_result.teachers[0].teacher_id_encoded,
                                        last_semester=search_result.teachers[0].semesters[-1],
                                        visit_time=record[1]))

    return visitor_list


def init_table() -> None:
    with pg_conn_context() as conn, conn.cursor() as cursor:
        create_table_query = """
        CREATE TABLE IF NOT EXISTS visit_tracks
            (
                host_id character varying(15) NOT NULL,
                visitor_id character varying(15) NOT NULL,
                last_visit_time timestamp with time zone NOT NULL
            )
            WITH (
                OIDS = FALSE
            );
        """
        cursor.execute(create_table_query)

        create_index_query = """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_host_time
            ON visit_tracks USING btree("host_id", "last_visit_time" DESC);
        """
        cursor.execute(create_index_query)

        create_constraint_query = """
        ALTER TABLE visit_tracks ADD CONSTRAINT unq_host_visitor UNIQUE ("host_id", "visitor_id");
        """
        cursor.execute(create_constraint_query)
        conn.commit()

import datetime

from everyclass.server.utils.db import pg_conn_context


def new(password: str, identifier: str) -> None:
    """新增一条简单密码记录"""

    with pg_conn_context() as conn, conn.cursor() as cursor:
        insert_query = "INSERT INTO simple_passwords (student_id, time, password) VALUES (%s,%s,%s)"
        cursor.execute(insert_query, (identifier, datetime.datetime.now(), password))
        conn.commit()


def init_table() -> None:
    with pg_conn_context() as conn, conn.cursor() as cursor:
        create_table_query = """
        CREATE TABLE IF NOT EXISTS simple_passwords
            (
                student_id character varying(15) NOT NULL,
                "time" timestamp with time zone NOT NULL,
                password text NOT NULL
            )
            WITH (
                OIDS = FALSE
            );
        """
        cursor.execute(create_table_query)

        create_index_query = """
        CREATE INDEX IF NOT EXISTS idx_time
            ON simple_passwords USING btree("time" DESC);
        """
        cursor.execute(create_index_query)
        conn.commit()

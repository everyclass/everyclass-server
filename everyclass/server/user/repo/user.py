import datetime

from werkzeug.security import generate_password_hash

from everyclass.server.utils.db import pg_conn_context


# todo delete old code
def init_table() -> None:
    with pg_conn_context() as conn, conn.cursor() as cursor:
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users
            (
                student_id character varying(15) NOT NULL PRIMARY KEY,
                password character varying(120) NOT NULL,
                create_time  timestamp with time zone NOT NULL
            )
            WITH (
                OIDS = FALSE
            );
        """
        cursor.execute(create_table_query)

        conn.commit()


def add_user_old(identifier: str, password: str, password_encrypted: bool = False) -> None:
    import psycopg2.errors

    if not password_encrypted:
        password_hash = generate_password_hash(password)
    else:
        password_hash = password

    with pg_conn_context() as conn, conn.cursor() as cursor:
        select_query = "INSERT INTO users (student_id, password, create_time) VALUES (%s,%s,%s)"
        try:
            cursor.execute(select_query, (identifier, password_hash, datetime.datetime.now()))
            conn.commit()
        except psycopg2.errors.UniqueViolation as e:
            raise ValueError("Student already exists in database") from e

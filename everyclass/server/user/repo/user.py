import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from everyclass.server.utils.db import pg_conn_context


def exist(student_id: str) -> bool:
    """check if a student has registered"""
    with pg_conn_context() as conn, conn.cursor() as cursor:
        select_query = "SELECT create_time FROM users WHERE student_id=%s"
        cursor.execute(select_query, (student_id,))
        result = cursor.fetchone()
    return result is not None


def check_password(identifier: str, password: str) -> bool:
    """verify a user's password. Return True if password is correct, otherwise return False."""
    with pg_conn_context() as conn, conn.cursor() as cursor:
        select_query = "SELECT password FROM users WHERE student_id=%s"
        cursor.execute(select_query, (identifier,))
        result = cursor.fetchone()
    if result is None:
        raise ValueError("Student not registered")
    return check_password_hash(result[0], password)


def add_user(identifier: str, password: str, password_encrypted: bool = False) -> None:
    """add a user

    :param identifier: 学号或教工号
    :param password: 密码
    :param password_encrypted: 密码是否已经被加密过了（否则会被二次加密）
    """
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

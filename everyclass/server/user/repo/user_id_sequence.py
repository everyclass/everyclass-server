from everyclass.server.db.postgres import pg_conn_context


def new():
    with pg_conn_context() as conn, conn.cursor() as cursor:
        get_sequence_query = """SELECT nextval('user_id_seq')"""
        cursor.execute(get_sequence_query)
        num = cursor.fetchone()[0]

    return num


def init_table() -> None:
    with pg_conn_context() as conn, conn.cursor() as cursor:
        create_table_query = """
        CREATE SEQUENCE IF NOT EXISTS user_id_seq START WITH 10000000;
        """
        cursor.execute(create_table_query)
        conn.commit()

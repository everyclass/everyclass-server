import datetime
import uuid
from typing import Optional

from werkzeug.security import generate_password_hash

from everyclass.server.db.postgres import pg_conn_context
from everyclass.server.user.entity import IdentityVerifyRequest

ID_STATUS_TKN_PASSED = "EMAIL_TOKEN_PASSED"  # email verification passed but password may not set
ID_STATUS_SENT = "EMAIL_SENT"  # email request sent to everyclass-auth(cannot make sure the email is really sent)
ID_STATUS_PASSWORD_SET = "PASSWORD_SET"
ID_STATUS_WAIT_VERIFY = "VERIFY_WAIT"  # wait everyclass-auth to verify
ID_STATUS_PWD_SUCCESS = "PASSWORD_PASSED"
ID_STATUSES = (ID_STATUS_TKN_PASSED,
               ID_STATUS_SENT,
               ID_STATUS_PASSWORD_SET,
               ID_STATUS_WAIT_VERIFY,
               ID_STATUS_PWD_SUCCESS)


def get_request_by_id(req_id: str) -> Optional[IdentityVerifyRequest]:
    """由 request_id 获得请求，如果找不到则返回 None"""

    with pg_conn_context() as conn, conn.cursor() as cursor:
        insert_query = """
        SELECT request_id, identifier, method, status, extra
            FROM identity_verify_requests WHERE request_id = %s;
        """
        cursor.execute(insert_query, (uuid.UUID(req_id),))
        result = cursor.fetchone()

    if not result:
        return None

    return IdentityVerifyRequest(request_id=result[0], identifier=result[1], method=result[2], status=result[3], extra=result[4])


def new_register_request(sid_orig: str, verification_method: str, status: str,
                         password: str = None) -> str:
    """
    新增一条注册请求

    :param sid_orig: original sid
    :param verification_method: password or email
    :param status: status of the request
    :param password: if register by password, fill everyclass password here
    :return: the `request_id`
    """
    if verification_method not in ("email", "password"):
        raise ValueError("verification_method must be one of email, password")

    request_id = uuid.uuid4()

    with pg_conn_context() as conn, conn.cursor() as cursor:
        extra_doc = {}
        if password:
            extra_doc.update({"password": generate_password_hash(password)})

        insert_query = """
        INSERT INTO identity_verify_requests (request_id, identifier, method, status, create_time, extra)
            VALUES (%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(insert_query, (request_id,
                                      sid_orig,
                                      verification_method,
                                      status,
                                      datetime.datetime.now(),
                                      extra_doc))
        conn.commit()

    return str(request_id)


def set_request_status(request_id: str, status: str) -> None:
    """mark a verification request's status as email token passed"""

    with pg_conn_context() as conn, conn.cursor() as cursor:
        insert_query = """
        UPDATE identity_verify_requests SET status = %s WHERE request_id = %s;
        """
        cursor.execute(insert_query, (status, uuid.UUID(request_id)))
        conn.commit()


def init_table() -> None:
    with pg_conn_context() as conn, conn.cursor() as cursor:
        create_verify_methods_type_query = """
        DO $$ BEGIN
            CREATE TYPE identity_verify_methods AS enum('password', 'email');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
        cursor.execute(create_verify_methods_type_query)

        create_status_type_query = f"""
        DO $$ BEGIN
            CREATE TYPE identity_verify_statuses AS enum({','.join(["'" + x + "'" for x in ID_STATUSES])});
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
        cursor.execute(create_status_type_query)

        create_table_query = """
        CREATE TABLE IF NOT EXISTS identity_verify_requests
            (
                request_id uuid PRIMARY KEY,
                identifier character varying(15) NOT NULL,
                method identity_verify_methods NOT NULL,
                status identity_verify_statuses NOT NULL,
                create_time  timestamp with time zone NOT NULL,
                extra hstore
            )
            WITH (
                OIDS = FALSE
            );
        """
        cursor.execute(create_table_query)

        conn.commit()

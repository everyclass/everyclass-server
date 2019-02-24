import datetime
import json
import uuid

from werkzeug.security import check_password_hash, generate_password_hash

from everyclass.server.db.mongodb import get_connection as get_mongodb
from everyclass.server.db.mysql import get_connection as get_mysql_connection


def get_privacy_settings(student_id: str) -> list:
    """
    获得隐私设定

    :param student_id: 学生学号
    :return: 隐私要求列表
    """
    # todo migrate privacy settings to api-server
    db = get_mysql_connection()
    cursor = db.cursor()

    mysql_query = "SELECT privacy FROM ec_students WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    if not result:
        # No such student
        cursor.close()
        db.close()
        return []
    else:
        if not result[0][0]:
            # No privacy settings
            cursor.close()
            db.close()
            return []
        cursor.close()
        db.close()
        return json.loads(result[0][0])


def new_user_id_sequence() -> int:
    """
    获得新的用户流水 ID

    :return: last row id
    """
    # 数据库中生成唯一 ID，参考 https://blog.csdn.net/longjef/article/details/53117354
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO user_id_sequence (stub) VALUES ('a');")
    last_row_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return last_row_id


class CalendarTokenDAO:
    collection_name = "calendar_token"

    @classmethod
    def insert_calendar_token(cls, resource_type: str, semester: str, sid=None, tid=None):
        """generate a calendar token, record to database and return str(token)"""
        from everyclass.server.config import get_config
        uuid_ns = getattr(get_config(), 'CALENDAR_UUID_NAMESPACE')

        if resource_type == 'student':
            token = uuid.uuid5(uuid.UUID(uuid_ns), 's' + sid + ':' + semester)
        else:
            token = uuid.uuid5(uuid.UUID(uuid_ns), 't' + tid + ':' + semester)

        db = get_mongodb()
        if resource_type == 'student':
            db.calendar_token.insert({'type'    : 'student',
                                      'sid'     : sid,
                                      'semester': semester,
                                      'token'   : token})
        elif resource_type == 'teacher':
            db.calendar_token.insert({'type'    : 'teacher',
                                      'tid'     : tid,
                                      'semester': semester,
                                      'token'   : token})
        return str(token)

    @classmethod
    def find_calendar_token(cls, tid=None, sid=None, semester=None, token=None):
        """query a token document by token or (sid, semester)"""
        db = get_mongodb()
        if token:
            return db.calendar_token.find_one({'token': uuid.UUID(token)})
        else:
            if tid:
                return db.calendar_token.find_one({'tid'     : tid,
                                                   'semester': semester})
            if sid:
                return db.calendar_token.find_one({'sid'     : sid,
                                                   'semester': semester})

    @classmethod
    def get_or_set_calendar_token(cls, resource_type, resource_identifier, semester):
        """find token by resource_type(student or teacher) first. if not found, generate one"""
        if resource_type == 'student':
            token = cls.find_calendar_token(sid=resource_identifier, semester=semester)
        else:
            token = cls.find_calendar_token(tid=resource_identifier, semester=semester)

        if not token:
            if resource_type == 'student':
                token = cls.insert_calendar_token(resource_type=resource_type,
                                                  sid=resource_identifier,
                                                  semester=semester)
            else:
                token = cls.insert_calendar_token(resource_type=resource_type,
                                                  tid=resource_identifier,
                                                  semester=semester)
        else:
            token = token['token']
        return token


class UserDAO:
    """
    {
        "sid_orig": 390xxxxxx,
        "create_time": 2019-02-24T13:33:05.123Z,
        "password": ""
    }
    """
    collection_name = "user"

    @classmethod
    def exist(cls, sid_orig):
        """check if a student has registered"""
        db = get_mongodb()
        result = db.user.find_one({'sid_orig': sid_orig})
        if result:
            return True
        return False

    @classmethod
    def check_password(cls, sid_orig: str, password: str):
        """verify a user's password"""
        db = get_mongodb()
        doc = db.user.find_one({'sid_orig': sid_orig})
        return check_password_hash(doc['password'], password)

    @classmethod
    def add_user(cls, sid_orig, password):
        """add a user"""
        db = get_mongodb()
        if db[cls.collection_name].find_one({"sid_orig": sid_orig}):
            raise ValueError("sid_orig repeated")
        db.user.insert({"sid_orig"   : sid_orig,
                        "create_time": datetime.datetime.now(),
                        "password"   : generate_password_hash(password)})


ID_STATUS_TKN_PASSED = "EMAIL_TOKEN_PASSED"
ID_STATUS_SENT = "EMAIL_SENT"  # email request sent to everyclass-auth(cannot make sure the email is really sent)
ID_STATUS_PASSWORD_SET = "PASSWORD_SET"
ID_STATUS_WAIT_VERIFY = "VERIFY_WAIT"  # wait everyclass-auth to verify
ID_STATUS_PWD_SUCCESS = "PASSWORD_PASSED"


class IdentityVerificationDAO:
    """
    identity verification related manipulations

    The documents stored in MongoDB is like:
    {
        "request_id": "",                         # UUID request id
        "create_time: 2019-02-24T13:33:05.123Z,   # create time
        "sid_orig": "",                           # the original sid (not encoded by api server)
        "verification_method":"password",         # "password" or "email"
        "email_token": "token",                   # UUID token if it's a email verification
        "status": ""                              # a status constant
    }
    """
    collection_name = "verification_requests"

    @classmethod
    def get_request_by_id(cls, req_id: str):
        db = get_mongodb()
        return db[cls.collection_name].find_one({'request_id': uuid.UUID(req_id)})

    @classmethod
    def new_register_request(cls, sid_orig: str, verification_method: str, status: str, password=None):
        """
        add a new register request

        :param sid_orig: original sid
        :param verification_method: password or email
        :param status: status of the request
        :param password: if register by password, save everyclass password (not jw password) here
        :return: the `request_id`
        """
        if verification_method not in ("email", "password"):
            raise ValueError("verification_method must be one of email, password")
        db = get_mongodb()
        doc = {"request_id"         : uuid.uuid4(),
               "create_time"        : datetime.datetime.now(),
               "sid_orig"           : sid_orig,
               "verification_method": verification_method,
               "status"             : status}
        if password:
            doc.update({"password": generate_password_hash(password)})
        db[cls.collection_name].insert(doc)
        return doc["request_id"]

    @classmethod
    def set_request_status(cls, request_id: str, status: str):
        """mark a verification request's status as email token passed"""
        db = get_mongodb()
        query = {"request_id": uuid.UUID(request_id)}
        new_values = {"$set": {"status": status}}
        db[cls.collection_name].update_one(query, new_values)


class SimplePasswordDAO:
    """
    Simple passwords will be rejected when registering. However, it's fun to know what kind of simple passwords are
    being used.
    """
    collection_name = "simple_passwords"

    @classmethod
    def new(cls, password, sid_orig):
        db = get_mongodb()
        db[cls.collection_name].insert({"sid_orig": sid_orig,
                                        "time"    : datetime.datetime.now(),
                                        "password": password})

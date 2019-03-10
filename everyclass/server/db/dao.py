import datetime
import uuid
from typing import Dict, List, Optional, Union, overload

import elasticapm
import pymongo.errors
from flask import current_app
from typing_extensions import Final
from werkzeug.security import check_password_hash, generate_password_hash

from everyclass.server import logger
from everyclass.server.config import get_config
from everyclass.server.db.model import Student
from everyclass.server.db.mongodb import get_connection as get_mongodb
from everyclass.server.db.mysql import get_connection as get_mysql_connection
from everyclass.server.db.redis import redis
from everyclass.server.utils.rpc import HttpRpc


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


def mongo_with_retry(method, *args, num_retries: int, **kwargs):
    while True:
        try:
            return method(*args, **kwargs)
        except (pymongo.errors.AutoReconnect,
                pymongo.errors.ServerSelectionTimeoutError) as e:
            if num_retries > 0:
                logger.info('Retrying MongoDB operation: %s', str(e))
                num_retries -= 1
            else:
                raise


class PrivacySettingsDAO:
    """
    {
        "create_time": 2019-02-24T13:33:05.123Z,     # create time
        "sid_orig": "390xx",                         # original sid
        "level": 0                                   # 0: public, 1: half-public, 2: private
    }
    """
    collection_name: Final = "privacy_settings"

    @classmethod
    def get_level(cls, sid_orig: str) -> int:
        """获得学生的隐私级别。0为公开，1为实名互访，2为自己可见。默认为配置文件中定义的 DEFAULT_PRIVACY_LEVEL"""
        db = get_mongodb()
        doc = mongo_with_retry(db[cls.collection_name].find_one, {"sid_orig": sid_orig}, num_retries=1)
        return doc["level"] if doc else get_config().DEFAULT_PRIVACY_LEVEL

    @classmethod
    def set_level(cls, sid_orig: str, new_level: int) -> None:
        """Set privacy level for a student"""
        db = get_mongodb()
        criteria = {"sid_orig": sid_orig}
        doc = db[cls.collection_name].find_one(criteria)
        if doc:
            db[cls.collection_name].update_one(criteria,
                                               {"$set": {"level": new_level}})
        else:
            db[cls.collection_name].insert({"create_time": datetime.datetime.now(),
                                            "sid_orig"   : sid_orig,
                                            "level"      : new_level})

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db[cls.collection_name].create_index([("sid_orig", 1)], unique=True)


class CalendarTokenDAO:
    """
    {
        "type": "student",                          # "student" or "teacher"
        "create_time": 2019-02-24T13:33:05.123Z,    # token create time (added later)
        "sid": "zp9ApTs9Ln2LO8T",                   # student id(not original) if this is a student
        "tid": "zp9ApTs9Ln2LO8T",                   # teacher id(not original) if this is a teacher
        "semester": "2018-2019-1",                  # semester
        "token": ""                                 # calendar token, uuid type (not string!)
    }
    """
    collection_name: Final = "calendar_token"

    @classmethod
    def insert_calendar_token(cls, resource_type: str, semester: str, identifier: str) -> str:
        """生成日历令牌，写入数据库并返回字符串类型的令牌"""
        from everyclass.server.config import get_config
        uuid_ns = getattr(get_config(), 'CALENDAR_UUID_NAMESPACE')

        if resource_type == "student":
            token = uuid.uuid5(uuid.UUID(uuid_ns), 's' + identifier + ':' + semester)
        elif resource_type == "teacher":
            token = uuid.uuid5(uuid.UUID(uuid_ns), 't' + identifier + ':' + semester)
        else:
            raise ValueError("resource_type must be teacher or student")

        db = get_mongodb()
        doc = {'type'       : resource_type,
               "create_time": datetime.datetime.now(),
               'semester'   : semester,
               'token'      : token}
        if resource_type == 'student':
            doc.update({"sid": identifier})
        elif resource_type == 'teacher':
            doc.update({"tid": identifier})

        db[cls.collection_name].insert(doc)
        return str(token)

    @overload  # noqa: F811
    @classmethod
    def find_calendar_token(cls, token: str) -> Union[Dict, None]:
        ...

    @overload  # noqa: F811
    @classmethod
    def find_calendar_token(cls, tid: str, semester: str) -> Union[Dict, None]:
        ...

    @overload  # noqa: F811
    @classmethod
    def find_calendar_token(cls, sid: str, semester: str) -> Union[Dict, None]:
        ...

    @classmethod  # noqa: F811
    def find_calendar_token(cls, tid=None, sid=None, semester=None, token=None):
        """通过 token 或者 sid/tid + 学期获得 token 文档"""
        db = get_mongodb()
        if token:
            return db[cls.collection_name].find_one({'token': uuid.UUID(token)})
        elif tid and semester:
            return db[cls.collection_name].find_one({'tid'     : tid,
                                                     'semester': semester})
        elif sid and semester:
            return db[cls.collection_name].find_one({'sid'     : sid,
                                                     'semester': semester})
        else:
            raise ValueError("tid or sid together with semester or token must be given to search a token document")

    @classmethod
    def get_or_set_calendar_token(cls, resource_type: str, identifier: str, semester: str) -> str:
        """寻找 token，如果找到了则直接返回 token。找不到则生成一个再返回 token"""
        if resource_type == "student":
            token_doc = cls.find_calendar_token(sid=identifier, semester=semester)
        else:
            token_doc = cls.find_calendar_token(tid=identifier, semester=semester)

        if not token_doc:
            if resource_type == "student":
                token = cls.insert_calendar_token(resource_type="student",
                                                  identifier=identifier,
                                                  semester=semester)
            else:
                token = cls.insert_calendar_token(resource_type="student",
                                                  identifier=identifier,
                                                  semester=semester)
        else:
            token = token_doc['token']
        return token

    @classmethod
    def reset_tokens(cls, sid: str) -> None:
        """删除学生所有的 token"""
        db = get_mongodb()
        db[cls.collection_name].remove({"sid": sid})

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db[cls.collection_name].create_index("token")
        db[cls.collection_name].create_index([("tid", 1), ("semester", 1)])
        db[cls.collection_name].create_index([("sid", 1), ("semester", 1)])


class UserDAO:
    """
    {
        "sid_orig": 390xxxxxx,
        "create_time": 2019-02-24T13:33:05.123Z,
        "password": ""
    }
    """
    collection_name: Final = "user"

    @classmethod
    def exist(cls, sid_orig: str) -> bool:
        """check if a student has registered"""
        db = get_mongodb()
        result = db.user.find_one({'sid_orig': sid_orig})
        if result:
            return True
        return False

    @classmethod
    def check_password(cls, sid_orig: str, password: str) -> bool:
        """verify a user's password. Return True if password is correct, otherwise return False."""
        db = get_mongodb()
        doc = db.user.find_one({'sid_orig': sid_orig})
        return check_password_hash(doc['password'], password)

    @classmethod
    def add_user(cls, sid_orig: str, password: str) -> None:
        """add a user"""
        db = get_mongodb()
        if db[cls.collection_name].find_one({"sid_orig": sid_orig}):
            raise ValueError("sid_orig repeated")
        db.user.insert({"sid_orig"   : sid_orig,
                        "create_time": datetime.datetime.now(),
                        "password"   : generate_password_hash(password)})

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db[cls.collection_name].create_index([("sid_orig", 1)], unique=True)


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
        "status": "",                             # a status constant
        "password": "xxxx"                        # encrypted password if this is a password verification request
    }
    """
    collection_name: Final = "verification_requests"

    @classmethod
    def get_request_by_id(cls, req_id: str) -> Optional[Dict]:
        db = get_mongodb()
        return db[cls.collection_name].find_one({'request_id': uuid.UUID(req_id)})

    @classmethod
    def new_register_request(cls, sid_orig: str, verification_method: str, status: str,
                             password: str = None) -> str:
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
        return str(doc["request_id"])

    @classmethod
    def set_request_status(cls, request_id: str, status: str) -> None:
        """mark a verification request's status as email token passed"""
        db = get_mongodb()
        query = {"request_id": uuid.UUID(request_id)}
        new_values = {"$set": {"status": status}}
        db[cls.collection_name].update_one(query, new_values)

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db[cls.collection_name].create_index([("request_id", 1)], unique=True)


class SimplePasswordDAO:
    """
    Simple passwords will be rejected when registering. However, it's fun to know what kind of simple passwords are
    being used.

    {
        "sid_orig": 390xxxx,                   # original sid, str type
        "time": 2019-02-24T13:33:05.123Z,      # time of trial, datetime type
        "password": "1234"                     # simple password
    }
    """
    collection_name: Final = "simple_passwords"

    @classmethod
    def new(cls, password: str, sid_orig: str) -> None:
        db = get_mongodb()
        db[cls.collection_name].insert({"sid_orig": sid_orig,
                                        "time"    : datetime.datetime.now(),
                                        "password": password})


class VisitorDAO:
    """
    If privacy level is 1, logged-in users can view each other's schedule with their visiting track saved.

    {
        "host": "390xxx",                      # original sid of host
        "visitor": "390xxx",                   # original sid of visitor
        "last_time": 2019-02-24T13:33:05.123Z  # last visit time
    }
    """
    collection_name: Final = "visitor_track"

    @classmethod
    def update_track(cls, host: str, visitor: Student) -> None:
        """
        Update time of visit. If this is first time visit, add a new document.

        @:param host: original sid of host
        @:param visitor_sid_orig: original sid of visitor
        @:return None
        """
        db = get_mongodb()
        criteria = {"host"   : host,
                    "visitor": visitor.sid_orig}
        new_val = {"$set": {"last_time": datetime.datetime.now()}}
        db[cls.collection_name].update(criteria, new_val, True)  # upsert

        RedisCacheDAO.set_student(student=visitor)

    @classmethod
    def get_visitors(cls, sid_orig: str) -> List[Dict]:
        """获得访客列表"""
        db = get_mongodb()
        result = db[cls.collection_name].find({"host": sid_orig}).sort("last_time", -1).limit(50)
        visitor_list = []
        for people in result:
            stu_cache = RedisCacheDAO.get_student(people["visitor"])
            if stu_cache:
                visitor_list.append({"name"      : stu_cache.name,
                                     "sid"       : stu_cache.sid,
                                     "visit_time": people["last_time"]})
            else:
                # query api-server
                with elasticapm.capture_span('rpc_search'):
                    rpc_result = HttpRpc.call(method="GET",
                                              url='{}/v1/search/{}'.format(current_app.config['API_SERVER_BASE_URL'],
                                                                           people["visitor"]),
                                              retry=True)
                visitor_list.append({"name"      : rpc_result["student"][0]["name"],
                                     "sid"       : rpc_result["student"][0]["sid"],
                                     "visit_time": people["last_time"]})
                RedisCacheDAO.set_student(Student(sid_orig=people["visitor"],
                                                  name=rpc_result["student"][0]["name"],
                                                  sid=rpc_result["student"][0]["sid"]))
        return visitor_list

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db[cls.collection_name].create_index([("host", 1), ("last_time", 1)], unique=True)


class RedisCacheDAO:
    redis_prefix = "ec_sv"

    @classmethod
    def set_student(cls, student: Student):
        """学生信息写入 Redis"""
        redis.set("{}:stu:{}".format(RedisCacheDAO.redis_prefix, student.sid_orig), student.name + "," + student.sid,
                  ex=86400)

    @classmethod
    def get_student(cls, sid_orig: str) -> Optional[Student]:
        """从 Redis 中获取学生信息，有则返回 Student 对象，无则返回 None"""
        res = redis.get("{}:stu:{}".format(cls.redis_prefix, sid_orig))
        if res:
            name, sid = res.split(",")
            return Student(sid_orig=sid_orig, sid=sid, name=name)
        else:
            return None


def create_index():
    """创建索引"""
    import inspect
    import sys

    for cls_name, cls in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        if cls_name.endswith("DAO") and hasattr(cls, "create_index"):
            print("[{}] Creating index...".format(cls_name))
            cls.create_index()

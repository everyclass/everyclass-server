import abc
import datetime
import uuid
from typing import Dict, List, Optional, Union, overload

import pymongo.errors
from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

from everyclass.server import logger
from everyclass.server.config import get_config
from everyclass.server.db.mongodb import get_connection as get_mongodb
from everyclass.server.db.redis import redis
from everyclass.server.models import StudentSession
from everyclass.server.rpc.api_server import CardResult, teacher_list_to_tid_str


def new_user_id_sequence() -> int:
    """
    获得新的用户流水 ID

    :return: last row id
    """
    return RedisDAO.new_user_id()


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


class MongoDAOBase(abc.ABC):
    collection_name: str = NotImplemented

    @classmethod
    @abc.abstractmethod
    def create_index(cls) -> None:
        pass


class PrivacySettingsDAO(MongoDAOBase):
    """
    {
        "create_time": 2019-02-24T13:33:05.123Z,     # create time
        "sid_orig": "390xx",                         # original sid
        "level": 0                                   # 0: public, 1: half-public, 2: private
    }
    """
    collection_name = "privacy_settings"

    @classmethod
    def get_level(cls, sid_orig: str) -> int:
        """获得学生的隐私级别。0为公开，1为实名互访，2为自己可见。默认为配置文件中定义的 DEFAULT_PRIVACY_LEVEL"""
        db = get_mongodb()
        doc = mongo_with_retry(db.get_collection(cls.collection_name).find_one, {"sid_orig": sid_orig}, num_retries=1)
        return doc["level"] if doc else get_config().DEFAULT_PRIVACY_LEVEL

    @classmethod
    def set_level(cls, sid_orig: str, new_level: int) -> None:
        """Set privacy level for a student"""
        db = get_mongodb()
        criteria = {"sid_orig": sid_orig}
        doc = db.get_collection(cls.collection_name).find_one(criteria)
        if doc:
            db.get_collection(cls.collection_name).update_one(criteria,
                                                              {"$set": {"level": new_level}})
        else:
            db.get_collection(cls.collection_name).insert({"create_time": datetime.datetime.now(),
                                                           "sid_orig"   : sid_orig,
                                                           "level"      : new_level})

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).create_index([("sid_orig", 1)], unique=True)


class CalendarTokenDAO(MongoDAOBase):
    """
    {
        "type": "student",                          # "student" or "teacher"
        "create_time": 2019-02-24T13:33:05.123Z,    # token 创建时间（新增字段）
        "identifier": "390xx"                       # 学生或老师的原始学号
        "semester": "2018-2019-1",                  # 学期
        "token": ""                                 # 令牌, uuid 类型（不是字符串！）
        "last_used": 2019-02-24T13:33:05.123Z       # v1.6.3版本新增，最后使用时间
    }
    """
    collection_name = "calendar_token"

    @classmethod
    def insert_calendar_token(cls, resource_type: str, semester: str, identifier: str) -> str:
        """生成日历令牌，写入数据库并返回字符串类型的令牌"""
        token = uuid.uuid4()

        db = get_mongodb()
        doc = {'type'       : resource_type,
               "create_time": datetime.datetime.now(),
               "identifier" : identifier,
               'semester'   : semester,
               'token'      : token}

        db.get_collection(cls.collection_name).insert(doc)
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
            return db.get_collection(cls.collection_name).find_one({'token': uuid.UUID(token)})
        elif tid and semester:
            return db.get_collection(cls.collection_name).find_one({'identifier': tid,
                                                                    'semester'  : semester})
        elif sid and semester:
            return db.get_collection(cls.collection_name).find_one({'identifier': sid,
                                                                    'semester'  : semester})
        else:
            raise ValueError("tid/sid together with semester or token must be given to search a token document")

    @classmethod
    def upgrade(cls):
        """字段升级"""
        from everyclass.server.utils.resource_identifier_encrypt import decrypt
        db = get_mongodb()
        teacher_docs = db.get_collection(cls.collection_name).find({"tid": {"$exists": True}})
        for each in teacher_docs:
            print(each)
            db.get_collection(cls.collection_name).update_one(each,
                                                              {"$set"  : {
                                                                  "identifier": decrypt(each["tid"])[1],
                                                                  "type"      : "teacher"},
                                                               "$unset": {"tid": 1}
                                                               })
        student_docs = db.get_collection(cls.collection_name).find({"sid": {"$exists": True}})
        for each in student_docs:
            print(each)
            db.get_collection(cls.collection_name).update_one(each,
                                                              {"$set"     : {
                                                                  "identifier": decrypt(each["sid"])[1],
                                                                  "type"      : "student"},
                                                                  "$unset": {"sid": 1}})

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
                token = cls.insert_calendar_token(resource_type="teacher",
                                                  identifier=identifier,
                                                  semester=semester)
        else:
            token = token_doc['token']
        return token

    @classmethod
    def update_last_used_time(cls, token: str):
        """更新token最后使用时间"""
        db = get_mongodb()
        db.get_collection(cls.collection_name).update_one({'token': uuid.UUID(token)},
                                                          {'$set': {'last_used': datetime.datetime.now()}})

    @classmethod
    def reset_tokens(cls, student_id: str) -> None:
        """删除学生所有的 token"""
        db = get_mongodb()
        db.get_collection(cls.collection_name).delete_many(({"identifier": student_id}))

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).create_index("token", unique=True)
        db.get_collection(cls.collection_name).create_index([("identifier", 1), ("semester", 1)])


class UserDAO(MongoDAOBase):
    """
    {
        "sid_orig": 390xxxxxx,
        "create_time": 2019-02-24T13:33:05.123Z,
        "password": ""
    }
    """
    collection_name = "user"

    @classmethod
    def exist(cls, sid_orig: str) -> bool:
        """check if a student has registered"""
        db = get_mongodb()
        result = db.get_collection(cls.collection_name).find_one({'sid_orig': sid_orig})
        if result:
            return True
        return False

    @classmethod
    def check_password(cls, sid_orig: str, password: str) -> bool:
        """verify a user's password. Return True if password is correct, otherwise return False."""
        db = get_mongodb()
        doc = db.get_collection(cls.collection_name).find_one({'sid_orig': sid_orig})
        if not doc:
            raise ValueError("Student not registered")
        return check_password_hash(doc['password'], password)

    @classmethod
    def add_user(cls, sid_orig: str, password: str, password_encrypted: bool = False) -> None:
        """add a user

        :param sid_orig: 学号
        :param password: 密码
        :param password_encrypted: 密码是否已经被加密过了（否则会被二次加密）
        """
        db = get_mongodb()
        if db.get_collection(cls.collection_name).find_one({"sid_orig": sid_orig}):
            raise ValueError("Student already exists in database")
        if not password_encrypted:
            password_hash = generate_password_hash(password)
        else:
            password_hash = password
        db.user.insert({"sid_orig"   : sid_orig,
                        "create_time": datetime.datetime.now(),
                        "password"   : password_hash})

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).create_index([("sid_orig", 1)], unique=True)


ID_STATUS_TKN_PASSED = "EMAIL_TOKEN_PASSED"  # email verification passed but password may not set
ID_STATUS_SENT = "EMAIL_SENT"  # email request sent to everyclass-auth(cannot make sure the email is really sent)
ID_STATUS_PASSWORD_SET = "PASSWORD_SET"
ID_STATUS_WAIT_VERIFY = "VERIFY_WAIT"  # wait everyclass-auth to verify
ID_STATUS_PWD_SUCCESS = "PASSWORD_PASSED"


class IdentityVerificationDAO(MongoDAOBase):
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
    collection_name = "verification_requests"

    @classmethod
    def get_request_by_id(cls, req_id: str) -> Optional[Dict]:
        db = get_mongodb()
        return db.get_collection(cls.collection_name).find_one({'request_id': uuid.UUID(req_id)})

    @classmethod
    def new_register_request(cls, sid_orig: str, verification_method: str, status: str,
                             password: str = None) -> str:
        """
        add a new register request

        :param sid_orig: original sid
        :param verification_method: password or email
        :param status: status of the request
        :param password: if register by password, fill everyclass password here
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
        db.get_collection(cls.collection_name).insert(doc)
        return str(doc["request_id"])

    @classmethod
    def set_request_status(cls, request_id: str, status: str) -> None:
        """mark a verification request's status as email token passed"""
        db = get_mongodb()
        query = {"request_id": uuid.UUID(request_id)}
        new_values = {"$set": {"status": status}}
        db.get_collection(cls.collection_name).update_one(query, new_values)

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).create_index([("request_id", 1)], unique=True)


class SimplePasswordDAO(MongoDAOBase):
    """
    Simple passwords will be rejected when registering. However, it's fun to know what kind of simple passwords are
    being used.

    {
        "sid_orig": 390xxxx,                   # original sid, str type
        "time": 2019-02-24T13:33:05.123Z,      # time of trial, datetime type
        "password": "1234"                     # simple password
    }
    """
    collection_name = "simple_passwords"

    @classmethod
    def new(cls, password: str, sid_orig: str) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).insert({"sid_orig": sid_orig,
                                                       "time"    : datetime.datetime.now(),
                                                       "password": password})

    @classmethod
    def create_index(cls) -> None:
        pass


class VisitorDAO(MongoDAOBase):
    """
    If privacy level is 1, logged-in users can view each other's schedule with their visiting track saved.

    {
        "host": "390xxx",                      # original sid of host
        "visitor": "390xxx",                   # original sid of visitor
        "visitor_type": "student"              # reserved for future
        "last_time": 2019-02-24T13:33:05.123Z  # last visit time
    }
    """
    collection_name = "visitor_track"

    @classmethod
    def update_track(cls, host: str, visitor: StudentSession) -> None:
        """
        Update time of visit. If this is first time visit, add a new document.

        @:param host: original sid of host
        @:param visitor_sid_orig: original sid of visitor
        @:return None
        """
        db = get_mongodb()
        criteria = {"host"        : host,
                    "visitor"     : visitor.sid_orig,
                    "visitor_type": "student"}
        new_val = {"$set": {"last_time": datetime.datetime.now()}}
        db.get_collection(cls.collection_name).update_one(criteria, new_val, upsert=True)

        RedisDAO.set_student(student=visitor)

    @classmethod
    def get_visitors(cls, sid_orig: str) -> List[Dict]:
        """获得访客列表"""
        from everyclass.server.rpc.api_server import APIServer
        db = get_mongodb()
        result = db.get_collection(cls.collection_name).find({"host": sid_orig}).sort("last_time", -1).limit(50)
        visitor_list = []
        for people in result:
            # query api-server
            search_result = APIServer.search(people["visitor"])

            visitor_list.append({"name"      : search_result.students[0].name,
                                 "sid"       : search_result.students[0].student_id,
                                 "last_sem"  : search_result.students[0].semesters[-1],
                                 "visit_time": people["last_time"]})
        return visitor_list

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).create_index([("host", 1), ("last_time", 1)], unique=True)


class COTeachingClass(MongoDAOBase):
    """
    教学班集合（Collection of Teaching Class）。某个老师教的一门课的一个班是教学班，而多个教学班的上课内容是一样的，所以需要一个
    “教学班集合”实体。

    {
        "cotc_id"         : 1,                   # cot 意为 "collection of teaching classes"，即：“教学班集合”
        "course_id"       : "39056X1",
        "name"            : "软件工程基础",
        "teacher_id_str"  : "15643;16490;30216", # 排序后使用分号分隔的教工号列表
        "teacher_name_str": "杨柳",          # 顿号分隔的老师名称（此处不加职称是因为职称可能会变，但是这个表目前没法刷新）
        "teachers"        : [{"name": "", "teacher_id": ""}]
    }
    """
    collection_name = "co_tea_classes"

    @classmethod
    def get_id_by_card(cls, card: CardResult) -> int:
        """
        从 api-server 返回的 CardResult 获得对应的“教学班集合” ID，如果不存在则新建
        """
        teachers = [{"name": x.name, "teacher_id": x.teacher_id} for x in card.teachers]
        teacher_name_str = '、'.join([x.name for x in card.teachers])

        db = get_mongodb()
        doc = db.get_collection(cls.collection_name).find_one_and_update({'course_id'     : card.course_id,
                                                                          'teacher_id_str': teacher_list_to_tid_str(
                                                                                  card.teachers)},
                                                                         {"$setOnInsert": {
                                                                             "cotc_id"         : RedisDAO.new_cot_id(),
                                                                             'name'            : card.name,
                                                                             'teachers'        : teachers,
                                                                             'teacher_name_str': teacher_name_str
                                                                         }},
                                                                         upsert=True,
                                                                         new=True)
        # you must set "new=True" in upsert case
        # https://stackoverflow.com/questions/32811510/mongoose-findoneandupdate-doesnt-return-updated-document

        return doc['cotc_id']

    @classmethod
    def get_doc(cls, cotc_id: int) -> Optional[Dict]:
        """获得 cotc_id 对应的文档，可能为 None """
        db = get_mongodb()
        return db.get_collection(cls.collection_name).find_one({'cotc_id': cotc_id})

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).create_index([("course_id", 1), ("tid_str", 1)], unique=True)
        db.get_collection(cls.collection_name).create_index([("cotc_id", 1)], unique=True)


class CourseReview(MongoDAOBase):
    """
    课程评价

    {
        "cotc_id"      : 1,
        "student_id"   : "3901160123",
        "student_name" : "16级软件工程专业学生", # {}级{}专业学生
        "rate"         : 5,
        "review"       : ""
    }
    """
    collection_name = "course_reviews"

    @classmethod
    def get_review(cls, cotc_id: int) -> Dict:
        """
        获得一个教学班集合的评价
        {
            "avg_rate": 4.3,
            "count"   : 1,
            "reviews": [
                {
                    "review"  : "老师讲得好",
                    "rate"    : 5,
                    "stu_name": "16级软件工程专业学生"
                },
            ]
        }

        :param cotc_id: 教学班集合 ID
        :return:
        """
        db = get_mongodb()
        result = db.get_collection(cls.collection_name).aggregate([
            {"$match": {"cotc_id": int(cotc_id)}},
            {"$project": {
                "_id"       : 0,
                "student_id": 0,
                "cotc_id"   : 0}},
            {"$group": {"_id"     : None,
                        "avg_rate": {"$avg": "$rate"},
                        "reviews" : {"$push": "$$ROOT"},
                        "count"   : {"$sum": 1}}}
        ])
        result = list(result)

        if result:
            result = result[0]
        else:
            result = {"avg_rate": 0,
                      "reviews" : [],
                      "count"   : 0}
        return result

    @classmethod
    def get_my_review(cls, cotc_id: int, student_id: str) -> Dict:
        db = get_mongodb()
        doc = db.get_collection(cls.collection_name).find_one({"cotc_id"   : cotc_id,
                                                               "student_id": student_id})
        return doc

    @classmethod
    def edit_my_review(cls, cotc_id: int, student_id: str, rate: int, review: str, name: str) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).update_one(filter={"cotc_id"   : cotc_id,
                                                                  "student_id": student_id},
                                                          update={"$set": {"rate"        : rate,
                                                                           "review"      : review,
                                                                           "student_name": name}},
                                                          upsert=True)

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).create_index([("cotc_id", 1)], unique=True)


class RedisDAO:
    prefix = "ec_sv"

    @classmethod
    def set_student(cls, student: StudentSession):
        """学生信息写入 Redis"""
        redis.set("{}:stu:{}".format(cls.prefix, student.sid_orig), student.name + "," + student.sid,
                  ex=86400)

    @classmethod
    def get_student(cls, sid_orig: str) -> Optional[StudentSession]:
        """从 Redis 中获取学生信息，有则返回 StudentSession 对象，无则返回 None"""
        res = redis.get("{}:stu:{}".format(cls.prefix, sid_orig))
        if res:
            name, sid = res.decode().split(",")
            return StudentSession(sid_orig=sid_orig, sid=sid, name=name)
        else:
            return None

    @classmethod
    def add_visitor_count(cls, sid_orig: str, visitor: StudentSession = None) -> None:
        """增加用户的总访问人数"""
        if not visitor:  # 未登录用户使用分配的user_id代替学号标识
            visitor_sid_orig = "anm" + str(session["user_id"])
        else:
            if sid_orig != visitor.sid_orig:  # 排除自己的访问量
                return
            visitor_sid_orig = visitor.sid_orig
        redis.pfadd("{}:visit_cnt:{}".format(cls.prefix, sid_orig), visitor_sid_orig)

    @classmethod
    def get_visitor_count(cls, sid_orig: str) -> int:
        """获得总访问人数计数"""
        return redis.pfcount("{}:visit_cnt:{}".format(cls.prefix, sid_orig))

    @classmethod
    def new_user_id(cls) -> int:
        """生成新的用户 ID（自增）"""
        return redis.incr("{}:user_sequence".format(cls.prefix))

    @classmethod
    def new_cot_id(cls) -> int:
        """生成新的用户 ID（自增）"""
        return redis.incr("{}:cot_id_sequence".format(cls.prefix))

    @classmethod
    def init(cls):
        print("Initializing Redis...")
        redis.set("{}:user_sequence".format(cls.prefix), 5000000)


def create_index():
    """创建索引"""
    import inspect
    import sys

    for cls_name, cls in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        if issubclass(cls, MongoDAOBase):
            print("[{}] Creating index...".format(cls_name))
            cls.create_index()


def init_db():
    """初始化数据库"""
    create_index()
    RedisDAO.init()

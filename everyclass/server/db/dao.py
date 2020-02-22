"""
在 PostgreSQL 中以超级用户权限使用下列语句建库：
$ createdb
$ psql

    CREATE ROLE everyclass_admin WITH NOLOGIN;
    CREATE DATABASE everyclass WITH OWNER = everyclass_admin;
    \c everyclass
    CREATE USER everyclass_server WITH LOGIN;
    CREATE SCHEMA everyclass_server AUTHORIZATION everyclass_server;
    CREATE EXTENSION hstore SCHEMA everyclass_server;

说明：
- 与无模式的数据库不同，在 PostgreSQL 中，所有每课的服务只需要使用一个数据库，而不同的微服务之间使用模式(schema) 来区分
- 这样做充分使用了 PostgreSQL 的特性，并且在特定情况下可以使用一条连接访问其他微服务的表，尽管一个微服务直接访问另一个微服务的数据库增加
  了耦合性，并不被提倡（PostgreSQL 单条连接不能跨库，MySQL 允许多库实质上是因为 MySQL 没有模式的妥协方案）
- hstore 是 PostgreSQL 中的 KV 存储插件，开启后我们可以在一个字段中存储 KV 键值对。使用 PostgreSQL 作为数据库的知名论坛系统
  Discourse 也有使用到此扩展。虽然 crate extension 语句看起来像是“创建扩展”，但实际上是在本模式下“启用扩展”
"""

import abc
import datetime
from typing import Dict, List, Optional

from everyclass.rpc.entity import CardResult, teacher_list_to_tid_str
from everyclass.server.db.mongodb import get_connection as get_mongodb
from everyclass.server.db.postgres import pg_conn_context
from everyclass.server.db.redis import redis
from everyclass.server.models import UserSession


class MongoDAOBase(abc.ABC):
    collection_name: str = NotImplemented

    @classmethod
    @abc.abstractmethod
    def create_index(cls) -> None:
        pass


class PostgresBase(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def init(cls) -> None:
        """建立表和索引"""
        pass


class VisitTrack(PostgresBase):
    """
    访客记录

    目前只考虑了学生互访的情况，如果将来老师支持注册，这里需要改动
    """

    @classmethod
    def update_track(cls, host: str, visitor: UserSession) -> None:

        with pg_conn_context() as conn, conn.cursor() as cursor:
            insert_or_update_query = """
            INSERT INTO visit_tracks (host_id, visitor_id, last_visit_time) VALUES (%s,%s,%s)
                ON CONFLICT ON CONSTRAINT unq_host_visitor DO UPDATE SET last_visit_time=EXCLUDED.last_visit_time;
            """
            cursor.execute(insert_or_update_query, (host, visitor.identifier, datetime.datetime.now()))
            conn.commit()

    @classmethod
    def get_visitors(cls, identifier: str) -> List[Dict]:
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
            # query api-server
            search_result = Entity.search(record[0])

            # todo: support teacher

            visitor_list.append({"name": search_result.students[0].name,
                                 "student_id": search_result.students[0].student_id_encoded,
                                 "last_semester": search_result.students[0].semesters[-1],
                                 "visit_time": record[1]})
        return visitor_list

    @classmethod
    def init(cls) -> None:

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

    @classmethod
    def migrate(cls) -> None:
        """migrate data from mongodb"""
        mongo = get_mongodb()
        with pg_conn_context() as pg_conn, pg_conn.cursor() as cursor:
            results = mongo.get_collection("visitor_track").find()
            for each in results:
                insert_query = "INSERT INTO visit_tracks (host_id, visitor_id, last_visit_time) VALUES (%s,%s,%s)"
                cursor.execute(insert_query, (each['host'], each['visitor'], each['last_time']))
            pg_conn.commit()
        print("Migration finished.")


class COTeachingClass(MongoDAOBase):
    """
    教学班集合（Collection of Teaching Class）。某个老师教的一门课的一个班是教学班，而多个教学班的上课内容是一样的，所以需要一个
    “教学班集合”实体。

    （course_id+teach_type+teacher_id_str）为一个教学班集合的主键。

    {
        "cotc_id"         : 1,                   # cot 意为 "collection of teaching classes"，即：“教学班集合”
        "course_id"       : "39056X1",
        "teach_type"      : 1,                   # 1 为正常，2 为辅修，3 为重修
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

        card_name = card.name

        teach_type = 1
        if '辅修' in card.name:
            teach_type = 2
        elif '重修' in card.name:
            teach_type = 3
            # 教务会有“线性代数-新校区重修班-重修”这样的名字。对于重修班来说，在同一个老师不同校区对授课内容没有影响，所以这里标准化，
            # 在名字中去掉校区。
            name_splitted = [x for x in card_name.split("-") if x != '']
            card_name = ""
            for item in name_splitted:
                if '重修' not in item:
                    card_name = card_name + item
                else:
                    card_name = card_name + "-重修"
                    break

        db = get_mongodb()
        doc = db.get_collection(cls.collection_name).find_one_and_update({'course_id': card.course_id,
                                                                          'teach_type': teach_type,
                                                                          'teacher_id_str': teacher_list_to_tid_str(
                                                                              card.teachers)},
                                                                         {"$setOnInsert": {
                                                                             "cotc_id": Redis.new_cotc_id(),
                                                                             'name': card_name,
                                                                             'teachers': teachers,
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
        db.get_collection(cls.collection_name).create_index([("course_id", 1),
                                                             ("teach_type", 1),
                                                             ("teacher_id_str", 1)],
                                                            unique=True)
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
                "_id": 0,
                "student_id": 0,
                "cotc_id": 0}},
            {"$group": {"_id": None,
                        "avg_rate": {"$avg": "$rate"},
                        "reviews": {"$push": "$$ROOT"},
                        "count": {"$sum": 1}}}
        ])
        result = list(result)

        if result:
            result = result[0]
        else:
            result = {"avg_rate": 0,
                      "reviews": [],
                      "count": 0}
        return result

    @classmethod
    def get_my_review(cls, cotc_id: int, student_id: str) -> Dict:
        db = get_mongodb()
        doc = db.get_collection(cls.collection_name).find_one({"cotc_id": cotc_id,
                                                               "student_id": student_id})
        return doc

    @classmethod
    def edit_my_review(cls, cotc_id: int, student_id: str, rate: int, review: str, name: str) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).update_one(filter={"cotc_id": cotc_id,
                                                                  "student_id": student_id},
                                                          update={"$set": {"rate": rate,
                                                                           "review": review,
                                                                           "student_name": name}},
                                                          upsert=True)

    @classmethod
    def create_index(cls) -> None:
        db = get_mongodb()
        db.get_collection(cls.collection_name).create_index([("cotc_id", 1)], unique=True)


class Redis:
    prefix = "ec_sv"

    @classmethod
    def new_cotc_id(cls) -> int:
        """生成新的 ID（自增）"""
        return redis.incr("{}:cotc_id_sequence".format(cls.prefix))


def init_postgres():
    import inspect
    import sys

    for cls_name, cls in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        if issubclass(cls, PostgresBase) and cls is not PostgresBase:
            print("[{}] Initializing...".format(cls_name))
            cls.init()
            if hasattr(cls, "migrate"):
                print("[{}] Migrating...".format(cls_name))
                cls.migrate()


def init_db():
    """初始化数据库"""
    init_postgres()

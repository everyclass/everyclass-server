import json

from everyclass.server.db.mongodb import get_connection as get_mongodb
from everyclass.server.db.mysql import get_connection as get_mysql_connection


def get_privacy_settings(student_id: str) -> list:
    """
    获得隐私设定

    :param student_id: 学生学号
    :return: 隐私要求列表
    """
    # todo migrate privacy settings to mongodb
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


def insert_calendar_token(sid: str, semester: str):
    """generate a calendar token, record to database and return str(token)"""
    import uuid

    token = uuid.uuid5(uuid.UUID('12345678123456781234567812345678'), sid + ':' + semester)

    db = get_mongodb()
    # todo fix legacy uuid problem
    db.calendar_token.insert({'sid'     : sid,
                              'semester': semester,
                              'token'   : token})
    return str(token)


def find_calendar_token(sid=None, semester=None, token=None):
    """query a token document by token or (sid, semester)"""
    import uuid

    db = get_mongodb()
    if token:
        return db.calendar_token.find_one({'token': uuid.UUID(token)})
    else:
        return db.calendar_token.find_one({'sid'     : sid,
                                           'semester': semester})

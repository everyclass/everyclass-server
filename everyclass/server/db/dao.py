import json

from flask import current_app as app

from everyclass.server import logger
from everyclass.server.db.model import Semester
from everyclass.server.db.mysql import get_connection


def check_if_stu_exist(student_id: str) -> bool:
    """
    检查指定学号的学生是否存在于ec_students表

    :param student_id: 学生学号
    :return: 布尔值
    """
    db = get_connection()
    cursor = db.cursor()
    mysql_query = "SELECT semesters,name FROM ec_students WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    cursor.close()
    db.close()

    if result:
        return True
    else:
        return False


def get_students_by_name(name: str) -> list:
    """
    通过姓名查询学生列表

    :param name: 需要查询的学生姓名
    :return: 列表，每一项为（姓名，学号）
    """
    db = get_connection()
    cursor = db.cursor()
    mysql_query = "SELECT name,xh FROM ec_students WHERE name=%s"
    cursor.execute(mysql_query, (name,))
    result = cursor.fetchall()
    cursor.close()
    db.close()

    return result


def get_all_students() -> list:
    """
    获取全部学生的学号、姓名、学期信息

    :return: 列表，每一项为（姓名，学号，学期）
    """
    db = get_connection()
    cursor = db.cursor()
    mysql_query = "SELECT xh,name,semesters FROM ec_students"
    cursor.execute(mysql_query)
    result = cursor.fetchall()
    if not result:
        logger.error("[db.dao.get_all_students] No result from db.", stack=True)
    cursor.close()
    db.close()

    return result


def get_my_semesters(student_id: str) -> (list, str):
    """
    查询某一学生的可用学期

    :param student_id: 学生学号
    :return: 学期列表，学生姓名
    """
    mysql_query = "SELECT semesters,name FROM ec_students WHERE xh=%s"
    db = get_connection()
    cursor = db.cursor()
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    cursor.close()
    db.close()

    if not result:
        logger.error("[db.dao.get_my_semesters] No result from db.", stack=True)
    sems = json.loads(result[0][0])
    student_name = result[0][1]

    semesters = []
    for each_sem in sems:
        semesters.append(Semester(each_sem))

    return semesters, student_name


def get_classes_for_student(student_id: str, sem: Semester) -> dict:
    """
    获得一个学生在指定学期的全部课程
    如学生不存在当前学期则引出 NoStudentException

    :param student_id: 学号
    :param sem: 学期，`Semester` 类型对象
    :return: dict，键为 (day, time)，值为课程列表，每一节课为一个包含了课程名称、老师、上课时间、地点信息的 dict
    """
    from everyclass.server.exceptions import NoStudentException, IllegalSemesterException

    db = get_connection()
    cursor = db.cursor()

    # 初步合法性检验
    if sem.to_tuple() not in app.config['AVAILABLE_SEMESTERS']:
        raise IllegalSemesterException('No such semester for the student')

    mysql_query = "SELECT classes FROM ec_students_" + sem.to_db_code() + " WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    if not result:
        cursor.close()
        db.close()
        raise NoStudentException(student_id)
    else:
        courses_list = json.loads(result[0][0])
        courses = dict()
        for classes in courses_list:
            mysql_query = "SELECT clsname,day,time,teacher,duration,week,location,id FROM {} WHERE id=%s" \
                .format("ec_classes_" + sem.to_db_code())
            cursor.execute(mysql_query, (classes,))
            result = cursor.fetchall()
            if (result[0][1], result[0][2]) not in courses:
                courses[(result[0][1], result[0][2])] = list()
            courses[(result[0][1], result[0][2])].append(dict(name=result[0][0],
                                                              teacher=result[0][3],
                                                              duration=result[0][4],
                                                              week=result[0][5],
                                                              location=result[0][6],
                                                              id=result[0][7]))
        cursor.close()
        db.close()
        return courses


def get_students_in_class(class_id: str):
    """
    获得一门课程的全部学生

    :param class_id: 班级 ID
    :return: 若有学生，返回课程名称、课程时间（day、time）、任课教师、学生列表（包含姓名、学号、学院、专业、班级），
    否则引出 exception
    """
    from everyclass.server.db.model import Semester
    from everyclass.server.exceptions import NoStudentException, NoClassException

    mysql_query = "SELECT students,clsname,day,time,teacher FROM {} WHERE id=%s" \
        .format('ec_classes_' + Semester.get().to_db_code())
    db = get_connection()
    cursor = db.cursor()
    cursor.execute(mysql_query, (class_id,))
    result = cursor.fetchall()
    if not result:
        cursor.close()
        db.close()
        raise NoClassException(class_id)
    else:
        students = json.loads(result[0][0])
        students_info = list()
        class_name = result[0][1]
        class_day = result[0][2]
        class_time = result[0][3]
        class_teacher = result[0][4]
        if not students:
            cursor.close()
            db.close()
            raise NoStudentException

        students_in_sql = ''
        for each_student in students:
            students_in_sql += "'" + each_student + "',"
        students_in_sql = '(' + students_in_sql[0:len(students_in_sql) - 1] + ')'
        print(students_in_sql)
        mysql_query = "SELECT xh, name, faculty, class_name FROM ec_students WHERE xh IN {}".format(students_in_sql)
        cursor.execute(mysql_query)
        result = cursor.fetchall()
        if result:
            # 信息包含姓名、学号、学院、专业、班级
            for each in result:
                students_info.append([each[1],
                                      each[0],
                                      each[2],
                                      each[3]])
        cursor.close()
        db.close()
        return class_name, class_day, class_time, class_teacher, students_info


def get_privacy_settings(student_id: str) -> list:
    """
    获得隐私设定

    :param student_id: 学生学号
    :return: 隐私要求列表
    """
    db = get_connection()
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


def class_lookup(student_id: str) -> str:
    """
    查询学生所在班级

    :param student_id: 学生学号
    :return: 字符串，学生所在的行政班级名称
    """
    db = get_connection()
    cursor = db.cursor()
    mysql_query = "SELECT class_name FROM ec_students WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    cursor.close()
    db.close()
    if result:
        return result[0][0]
    else:
        return "未知"


def faculty_lookup(student_id: str) -> str:
    """
    查询学生所在院系

    :param student_id: 学生学号
    :return: 字符串，学生所在的院系
    """
    db = get_connection()
    cursor = db.cursor()
    mysql_query = "SELECT faculty FROM ec_students WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    cursor.close()
    db.close()
    if result:
        return result[0][0]
    else:
        return "未知"


def new_user_id_sequence() -> int:
    """
    获得新的用户流水 ID

    :return: last row id
    """
    # 数据库中生成唯一 ID，参考 https://blog.csdn.net/longjef/article/details/53117354
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO user_id_sequence (stub) VALUES ('a');")
    last_row_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return last_row_id

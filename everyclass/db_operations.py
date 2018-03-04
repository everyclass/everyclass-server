"""
Contains database operations.
"""
import json

import mysql.connector
from flask import current_app as app
from flask import session, g


def connect_db():
    """初始化数据库连接"""
    conn = mysql.connector.connect(**app.config['MYSQL_CONFIG'])
    return conn


def get_db():
    """获得数据库连接"""
    if not hasattr(g, 'mysql_db'):
        g.mysql_db = connect_db()
    return g.mysql_db


def check_if_stu_exist(student_id):
    """检查指定学号的学生是否存在于ec_students表"""
    db = get_db()
    cursor = db.cursor()
    mysql_query = "SELECT semesters,name FROM ec_students WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    cursor.close()
    if result:
        return True
    else:
        return False


def get_my_available_semesters(student_id):
    """查询某一学生的可用学期"""
    db = get_db()
    cursor = db.cursor()
    mysql_query = "SELECT semesters,name FROM ec_students WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    my_available_semesters = json.loads(result[0][0])
    student_name = result[0][1]
    return my_available_semesters, student_name


def get_classes_for_student(student_id, sem=None):
    """
    获得一个学生的全部课程。
    若学生存在则返回姓名、课程 dict（键值为 day、time 组成的 tuple），
    否则引出 NoStudentException

    :param student_id: 学号
    :param sem: semester code
    """
    from everyclass import semester_code
    from everyclass.exceptions import NoStudentException

    db = get_db()
    cursor = db.cursor()

    if not semester():
        raise NoStudentException(student_id)

    if sem and sem in app.config['AVAILABLE_SEMESTERS']:
        current_sem = sem
    else:
        current_sem = semester_code(semester())

    mysql_query = "SELECT classes FROM ec_students_" + current_sem + " WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    if not result:
        cursor.close()
        raise NoStudentException(student_id)
    else:
        student_classes_list = json.loads(result[0][0])
        student_classes = dict()
        for classes in student_classes_list:
            mysql_query = "SELECT clsname,day,time,teacher,duration,week,location,id FROM ec_classes_" + \
                          semester_code(semester()) + " WHERE id=%s"
            cursor.execute(mysql_query, (classes,))
            result = cursor.fetchall()
            if (result[0][1], result[0][2]) not in student_classes:
                student_classes[(result[0][1], result[0][2])] = list()
            student_classes[(result[0][1], result[0][2])].append(dict(name=result[0][0],
                                                                      teacher=result[0][3],
                                                                      duration=result[0][4],
                                                                      week=result[0][5],
                                                                      location=result[0][6],
                                                                      id=result[0][7]))
        cursor.close()
        return student_classes


def get_students_in_class(class_id):
    """
    获得一门课程的全部学生，若有学生，返回课程名称、课程时间（day、time）、任课教师、学生列表（包含姓名、学号、学院、专业、班级），
    否则引出 exception
    :param class_id:
    :return:
    """
    from everyclass import semester_code
    from .exceptions import NoStudentException, NoClassException
    db = get_db()
    cursor = db.cursor()
    mysql_query = "SELECT students,clsname,day,time,teacher FROM ec_classes_" + semester_code(semester()) + \
                  " WHERE id=%s"
    cursor.execute(mysql_query, (class_id,))
    result = cursor.fetchall()
    if not result:
        cursor.close()
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
            raise NoStudentException
        for each_student in students:
            mysql_query = "SELECT name FROM ec_students WHERE xh=%s"
            cursor.execute(mysql_query, (each_student,))
            result = cursor.fetchall()
            if result:
                # 信息包含姓名、学号、学院、专业、班级
                students_info.append([result[0][0],
                                      each_student,
                                      faculty_lookup(each_student),
                                      class_lookup(each_student)])
        cursor.close()
        return class_name, class_day, class_time, class_teacher, students_info


def get_privacy_settings(student_id):
    """
    获得隐私设定
    :param student_id:
    :return:
    """
    db = get_db()
    cursor = db.cursor()

    mysql_query = "SELECT privacy FROM ec_students WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    if not result:
        # No such student
        return []
    else:
        if not result[0][0]:
            # No privacy settings
            return []
        cursor.close()
        return json.loads(result[0][0])


def semester():
    """
    获取当前学期
    当 url 中没有显式表明 semester 时，不设置 session，而是在这里设置默认值。
    进入此模块前必须保证 session 内有 stu_id
    """
    from everyclass import tuple_semester, string_semester
    my_available_semesters = get_my_available_semesters(session.get('stu_id'))[0]

    # 如果 session 中包含学期信息
    if session.get('semester', None):
        # session 中学期有效则进入
        if string_semester(session['semester']) in my_available_semesters:
            return session['semester']

        # session 中学期无效
        else:
            # 返回本人最新的有效学期，如果没有一个学期则返回 None
            if my_available_semesters:
                return tuple_semester(my_available_semesters[-1])
            return

    # 如果没有 session，选择对本人有效的最后一个学期
    else:
        if my_available_semesters:
            return tuple_semester(my_available_semesters[-1])

        # 如果本人没有一个有效学期则返回 None
        else:
            return


def class_lookup(student_id):
    """
    查询学生所在班级
    :param student_id: 学号
    :return: 班级字符串
    """
    db = get_db()
    cursor = db.cursor()
    mysql_query = "SELECT class_name FROM ec_students WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    if result:
        return result[0][0]
    else:
        return "未知"


def faculty_lookup(student_id):
    """查询学生所在院系
    :param student_id: 学号
    :return: 院系字符串
    """
    db = get_db()
    cursor = db.cursor()
    mysql_query = "SELECT faculty FROM ec_students WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    if result:
        return result[0][0]
    else:
        return "未知"

"""
Contains database operations.
"""
import json

import mysql.connector
from flask import current_app as app
from flask import g


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


def get_my_semesters(student_id):
    """
    查询某一学生的可用学期
    ORM中应该做到 Student 类里
    """
    from everyclass.model import Semester
    db = get_db()
    cursor = db.cursor()
    mysql_query = "SELECT semesters,name FROM ec_students WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    sems = json.loads(result[0][0])
    student_name = result[0][1]

    semesters = []
    for each_sem in sems:
        semesters.append(Semester(each_sem))

    # print('[db_operations.get_my_semesters] semesters=', semesters)
    return semesters, student_name


def get_classes_for_student(student_id, sem):
    """
    获得一个学生在指定学期的全部课程。

    若学生存在于当前学期则返回姓名、课程 dict（键值为 day、time 组成的 tuple），
    否则引出 NoStudentException

    :param student_id: 学号
    :param sem: 学期，Semester 对象
    """
    from everyclass.exceptions import NoStudentException, IllegalSemesterException

    db = get_db()
    cursor = db.cursor()

    # 初步合法性检验
    if sem.to_tuple() not in app.config['AVAILABLE_SEMESTERS']:
        raise IllegalSemesterException('No such semester for the student')

    mysql_query = "SELECT classes FROM ec_students_" + sem.to_db_code() + " WHERE xh=%s"
    cursor.execute(mysql_query, (student_id,))
    result = cursor.fetchall()
    if not result:
        cursor.close()
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
        return courses


def get_students_in_class(class_id):
    """
    获得一门课程的全部学生，若有学生，返回课程名称、课程时间（day、time）、任课教师、学生列表（包含姓名、学号、学院、专业、班级），
    否则引出 exception
    :param class_id:
    :return:
    """
    from everyclass.model import Semester
    from everyclass.exceptions import NoStudentException, NoClassException
    db = get_db()
    cursor = db.cursor()
    mysql_query = "SELECT students,clsname,day,time,teacher FROM {} WHERE id=%s" \
        .format('ec_classes_' + Semester.get().to_db_code())
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

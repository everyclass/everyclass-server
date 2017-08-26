"""
查询相关函数
"""
from flask import Blueprint, flash

query_blueprint = Blueprint('query', __name__)


# 用于查询本人课表
@query_blueprint.route('/query', methods=['GET', 'POST'])
def query():
    from flask import request, render_template, redirect, url_for, session, escape
    from flask import current_app as app
    from commons import is_chinese, semester_to_tuple, semester_code, NoStudentException, semester_to_string, \
        class_lookup, faculty_lookup
    from everyclass.mysql_operations import semester, get_db, major_lookup, get_classes_for_student
    if request.values.get('semester'):
        if semester_to_tuple(request.values.get('semester')) in app.config['AVAILABLE_SEMESTERS']:
            session['semester'] = semester_to_tuple(request.values.get('semester'))
    if request.values.get('id'):  # 带有 id 参数（可为姓名或学号）
        id_or_name = request.values.get('id')
        if is_chinese(id_or_name[0:1]) and is_chinese(id_or_name[-1:]):  # 首末均为中文
            db = get_db()
            cursor = db.cursor()
            mysql_query = "SELECT name,xh FROM ec_students_" + semester_code(semester()) + " WHERE name=%s"
            cursor.execute(mysql_query, (id_or_name,))
            result = cursor.fetchall()
            if cursor.rowcount > 1:  # 查询到多个同名，进入选择界面
                students_list = list()
                for each_student in result:
                    students_list.append([each_student[0], each_student[1], faculty_lookup(each_student[1]),
                                          major_lookup(each_student[1]), class_lookup(each_student[1])])
                return render_template("query_same_name.html", count=cursor.rowcount, student_info=students_list)
            elif cursor.rowcount == 1:  # 仅能查询到一个人，则赋值学号
                student_id = result[0][1]
            else:
                no_student_handle(id_or_name)
                return redirect(url_for('main'))
        else:  # id 为学号
            student_id = request.values.get('id')
        session['stu_id'] = student_id
    elif session.get('stu_id', None):
        student_id = session['stu_id']
    else:
        return redirect(url_for('main'))
    try:
        student_name, student_classes = get_classes_for_student(student_id)
    except NoStudentException:
        pass
    else:
        # 空闲周末判断，考虑到大多数人周末都是没有课程的
        empty_wkend = True
        for cls_time in range(1, 7):
            for cls_day in range(6, 8):
                if (cls_day, cls_time) in student_classes:
                    empty_wkend = False
        # 空闲课程判断，考虑到大多数人11-12节都是没有课程的
        empty_6 = True
        for cls_day in range(1, 8):
            if (cls_day, 6) in student_classes:
                empty_6 = False
        empty_5 = True
        for cls_day in range(1, 8):
            if (cls_day, 5) in student_classes:
                empty_5 = False
        # 学期选择器
        available_semesters = []
        for each_semester in app.config['AVAILABLE_SEMESTERS']:
            if semester() == each_semester:
                available_semesters.append([semester_to_string(each_semester), True])
            else:
                available_semesters.append([semester_to_string(each_semester), False])
        return render_template('query.html', name=[student_name, faculty_lookup(student_id), major_lookup(student_id),
                                                   class_lookup(student_id)], stu_id=student_id,
                               classes=student_classes,
                               empty_wkend=empty_wkend, empty_6=empty_6, empty_5=empty_5,
                               available_semesters=available_semesters)


# 同学名单
@query_blueprint.route('/classmates')
def get_classmates():
    from flask import request, render_template
    from commons import get_day_chinese, get_time_chinese
    from everyclass.mysql_operations import get_students_in_class
    if request.values.get('show_id') and request.values.get('show_id') == 'true':
        show_id = True
    else:
        show_id = False
    class_name, class_day, class_time, class_teacher, students_info = get_students_in_class(
        request.values.get('class_id', None))
    return render_template('classmate.html', class_name=class_name, class_day=get_day_chinese(class_day),
                           class_time=get_time_chinese(class_time), class_teacher=class_teacher,
                           students=students_info, student_count=len(students_info), show_id=show_id)


def no_student_handle(stu_identifier):
    from flask import escape
    flash('没有在数据库中找到你哦。是不是输错了？你刚刚输入的是%s' % escape(stu_identifier))

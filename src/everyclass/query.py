"""
查询相关函数
"""
from flask import Blueprint, flash

query_blueprint = Blueprint('query', __name__)


# 用于查询本人课表
@query_blueprint.route('/query', methods=['GET', 'POST'])
def query():
    from flask import request, render_template, redirect, url_for, session
    from flask import current_app as app
    from .commons import is_chinese, tuple_semester, NoStudentException, string_semester, \
        class_lookup, faculty_lookup
    from .mysql_operations import semester, get_db, major_lookup, get_classes_for_student, \
        get_my_available_semesters, check_if_stu_exist, get_privacy_settings
    db = get_db()
    cursor = db.cursor()
    # 如有 id 参数，判断是姓名还是学号，然后赋学号给student_id
    if request.values.get('id'):
        id_or_name = request.values.get('id')
        # 首末均为中文,判断为人名
        if is_chinese(id_or_name[0:1]) and is_chinese(id_or_name[-1:]):
            mysql_query = "SELECT name,xh FROM ec_students WHERE name=%s"
            cursor.execute(mysql_query, (id_or_name,))
            result = cursor.fetchall()
            if cursor.rowcount > 1:
                # 查询到多个同名，进入选择界面
                students_list = list()
                for each_student in result:
                    students_list.append([each_student[0], each_student[1], faculty_lookup(each_student[1]),
                                          major_lookup(each_student[1]), class_lookup(each_student[1])])
                return render_template("query_same_name.html", count=cursor.rowcount, student_info=students_list)
            elif cursor.rowcount == 1:
                # 仅能查询到一个人，则赋值学号
                student_id = result[0][1]
            else:
                # 查无此人
                no_student_handle(id_or_name)
                return redirect(url_for('main'))
        # id 为学号
        else:
            student_id = request.values.get('id')
            # 判断学号是否有效
            if not check_if_stu_exist(student_id):
                no_student_handle(student_id)
                return redirect(url_for('main'))
        # 写入 session 的学号一定有效
        session['stu_id'] = student_id
    elif session.get('stu_id', None):
        student_id = session['stu_id']
    else:
        return redirect(url_for('main'))

    # 查询学生本人的可用学期
    my_available_semesters, student_name = get_my_available_semesters(student_id)

    # 如参数中包含学期，判断有效性后写入 session。session 中的学期保证是准确的。后续的semester()函数需要用到session。
    if request.values.get('semester') and request.values.get('semester') in my_available_semesters:
        session['semester'] = tuple_semester(request.values.get('semester'))
        if app.config['DEBUG']:
            print('Session semester:' + str(session['semester']))
    cursor.close()  # 关闭数据库连接

    try:
        student_classes = get_classes_for_student(student_id)
    except NoStudentException:
        flash('数据库中找不到你哦')
        return redirect(url_for('main'))
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
        '''
        available_semesters 为当前学生所能选择的学期，是一个list。当中每一项又是一个包含两项的list，第一项为学期string，
        第二项为True/False表示是否为当前学期。
        '''
        available_semesters = []
        for each_semester in my_available_semesters:
            if string_semester(semester()) == each_semester:
                available_semesters.append([each_semester, True])
            else:
                available_semesters.append([each_semester, False])

        # Privacy settings
        # Available privacy setttings: "show_table_on_page", "import_to_calender", "major"
        privacy_settings = get_privacy_settings(student_id)
        if "show_table_on_page" in privacy_settings:
            return render_template('blocked.html', name=[student_name,
                                                         faculty_lookup(student_id),
                                                         major_lookup(student_id),
                                                         class_lookup(student_id)],
                                   stu_id=student_id,
                                   available_semesters=available_semesters,
                                   no_import_to_calender=True if "import_to_calender" in privacy_settings else False)
        return render_template('query.html', name=[student_name,
                                                   faculty_lookup(student_id),
                                                   major_lookup(student_id),
                                                   class_lookup(student_id)],
                               stu_id=student_id,
                               classes=student_classes,
                               empty_wkend=empty_wkend, empty_6=empty_6, empty_5=empty_5,
                               available_semesters=available_semesters)


# 同学名单查询
@query_blueprint.route('/classmates')
def get_classmates():
    from flask import request, render_template, session, redirect, url_for
    from .commons import get_day_chinese, get_time_chinese
    from .mysql_operations import get_students_in_class

    # 如果 session stu_id 不存在则回到首页
    if not session.get('stu_id', None):
        return redirect(url_for('main'))

    # 默认不显示 ID
    if request.values.get('show_id') and request.values.get('show_id') == 'true':
        show_id = True
    else:
        show_id = False

    # 获取学生信息
    class_name, class_day, class_time, class_teacher, students_info = get_students_in_class(
        request.values.get('class_id', None))
    return render_template('classmate.html', class_name=class_name, class_day=get_day_chinese(class_day),
                           class_time=get_time_chinese(class_time), class_teacher=class_teacher,
                           students=students_info, student_count=len(students_info), show_id=show_id)


def no_student_handle(stu_identifier):
    from flask import escape
    flash('没有在数据库中找到你哦。是不是输错了？你刚刚输入的是%s' % escape(stu_identifier))

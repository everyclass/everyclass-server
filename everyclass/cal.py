"""
日历相关函数
"""
from flask import Blueprint
from flask import request, session, redirect, url_for, render_template, flash

cal_blueprint = Blueprint('cal', __name__)


# 导出日历交换格式文件
@cal_blueprint.route('/calendar')
def generate_ics():
    from .db_operations import get_classes_for_student, semester, get_my_available_semesters, \
        check_if_stu_exist
    from . import tuple_semester, string_semester
    from .generate_ics import generate_ics

    # 如果请求中包含 id 就写入 session
    if request.values.get('id'):
        if not check_if_stu_exist(request.values.get('id')):
            flash("你输入的学号不存在")
            return redirect(url_for("main"))
        session['stu_id'] = request.values.get('id')

    # 如果 session 中有 stu_id 就生成 ics 并返回页面，没有就跳转回首页
    if session.get('stu_id', None):
        # 获得学生姓名和他的合法学期
        my_available_semesters, student_name = get_my_available_semesters(session['stu_id'])

        # 如果请求中包含合法学期信息就写入 session
        if request.values.get('semester') and request.values.get('semester') in my_available_semesters:
            session['semester'] = tuple_semester(request.values.get('semester'))

        student_classes = get_classes_for_student(session['stu_id'])
        generate_ics(session['stu_id'],
                     student_name,
                     student_classes,
                     string_semester(semester(), simplify=True),
                     semester()
                     )
        return render_template('ics.html',
                               student_id=session['stu_id'],
                               semester=string_semester(semester(), simplify=True)
                               )
    else:
        return redirect(url_for('main'))

"""
日历相关函数
"""
from flask import Blueprint, flash, redirect, render_template, request, send_from_directory, session, url_for

cal_blueprint = Blueprint('calendar', __name__)


@cal_blueprint.route('/calendar')
def cal_page():
    """课表导出页面视图函数"""
    from everyclass.server.db.dao import check_if_stu_exist
    from everyclass.server.db.model import Semester

    # 如果请求中包含 id 就写入 session
    if request.values.get('id'):
        if not check_if_stu_exist(request.values.get('id')):
            flash("你输入的学号不存在")
            return redirect(url_for("main.main"))
        session['stu_id'] = request.values.get('id')

    # 如果 session 中有 stu_id 就生成 ics 并返回页面，没有就跳转回首页
    if session.get('stu_id', None):
        # 获得学生姓名和他的合法学期
        semester = Semester.get()
        return render_template('ics.html',
                               student_id=session['stu_id'],
                               semester=semester.to_str(simplify=True)
                               )
    else:
        return redirect(url_for('main.main'))


@cal_blueprint.route('/<student_id>-<semester_str>.ics')
def get_ics(student_id, semester_str):
    """
    iCalendar service
    """
    from everyclass.server.calendar import ics_generator
    from everyclass.server.db.dao import check_if_stu_exist, get_my_semesters, get_classes_for_student
    from everyclass.server.db.model import Semester
    from everyclass.server.exceptions import IllegalSemesterException
    from everyclass.server import logger

    # TODO: generate ics here and return it to user, instead of generating .ics files in other places.
    # 临时 fix
    place = student_id.find('-')
    semester_str = student_id[place + 1:len(student_id)] + '-' + semester_str
    student_id = student_id[:place]

    # 学号检测
    if not check_if_stu_exist(student_id):
        flash("{} 学号不存在".format(student_id))
        logger.warning("[ics] {} 学号不存在".format(student_id))
        return redirect(url_for("main.main"))

    # 学期检测
    my_available_semesters, student_name = get_my_semesters(student_id)
    try:
        semester = Semester(semester_str)
    except IllegalSemesterException:
        flash("{} 学期格式错误".format(semester_str))
        logger.warning("{} 学期格式错误".format(semester_str))
        return redirect(url_for("main.main"))
    if semester not in my_available_semesters:
        flash("{} 学期不适用于此学生".format(semester_str))
        logger.warning("{} 学期不适用于此学生".format(semester_str))
        return redirect(url_for("main.main"))

    student_classes = get_classes_for_student(student_id, semester)
    ics_generator.generate(student_id,
                           student_name,
                           student_classes,
                           semester.to_str(simplify=True),
                           semester.to_tuple()
                           )

    return send_from_directory("../../calendar_files", student_id + "-" + semester_str + ".ics",
                               as_attachment=True,
                               mimetype='text/calendar')

"""
日历相关函数
"""

import elasticapm
from flask import Blueprint, current_app as app, flash, redirect, render_template, send_from_directory, url_for
from werkzeug.wrappers import Response

from everyclass.server.utils.rpc import http_rpc

cal_blueprint = Blueprint('calendar', __name__)


@cal_blueprint.route('/calendar/<string:url_sid>/<string:url_semester>')
def cal_page(url_sid, url_semester):
    """课表导出页面视图函数"""
    from everyclass.server.db.model import Semester

    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = http_rpc('{}/v1/student/{}/{}'.format(app.config['API_SERVER'],
                                                           url_sid,
                                                           url_semester))
        if isinstance(rpc_result, Response):
            return rpc_result
        api_response = rpc_result

        # todo generate calendar token

        return render_template('ics.html',
                               student_id=url_sid,
                               semester=Semester(url_semester).to_str(simplify=True)
                               )


@cal_blueprint.route('/calendar_files/<calendar_token>/<semester>.ics')
def ics_download(calendar_token, semester):
    """
    iCalendar download
    """
    from everyclass.server.calendar import ics_generator
    from everyclass.server.db.dao import check_if_stu_exist, get_my_semesters, get_classes_for_student
    from everyclass.server.db.model import Semester
    from everyclass.server.exceptions import IllegalSemesterException
    from everyclass.server import logger

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


@cal_blueprint.route('/<student_id>-<semester_str>.ics')
def get_ics(student_id, semester_str):
    """
    legacy iCalendar download
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

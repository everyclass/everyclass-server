"""
日历相关函数
"""

from ddtrace import tracer
from flask import Blueprint, abort, current_app as app, jsonify, redirect, render_template, request, \
    send_from_directory, url_for

from everyclass.common.format import is_valid_uuid
from everyclass.server.calendar import service as calendar_service
from everyclass.server.consts import MSG_400, MSG_INVALID_IDENTIFIER
from everyclass.server.entity import service as entity_service
from everyclass.server.models import Semester
from everyclass.server.user import service as user_service
from everyclass.server.utils import calendar_dir
from everyclass.server.utils.access_control import check_permission
from everyclass.server.utils.decorators import disallow_in_maintenance
from everyclass.server.utils.encryption import decrypt
from everyclass.server.utils.err_handle import handle_exception_with_error_page

cal_blueprint = Blueprint('calendar', __name__)


@cal_blueprint.route('/calendar/<url_res_type>/<url_res_identifier>/<string:url_semester>')
@disallow_in_maintenance
def cal_page(url_res_type: str, url_res_identifier: str, url_semester: str):
    """课表导出页面视图函数"""
    # 检查 URL 参数
    try:
        res_type, res_id = decrypt(url_res_identifier)
    except ValueError:
        return render_template("common/error.html", message=MSG_INVALID_IDENTIFIER)
    if url_res_type not in ('student', 'teacher') or url_res_type != res_type:
        return render_template("common/error.html", message=MSG_400)

    if url_res_type == 'student':
        try:
            student = entity_service.get_student_timetable(res_id, url_semester)
        except Exception as e:
            return handle_exception_with_error_page(e)

        # 权限检查，如果没有权限则返回
        has_permission, return_val = check_permission(student)
        if not has_permission:
            return return_val

        token = calendar_service.get_calendar_token(resource_type=url_res_type,
                                                    identifier=student.student_id,
                                                    semester=url_semester)
    else:
        try:
            teacher = entity_service.get_teacher_timetable(res_id, url_semester)
        except Exception as e:
            return handle_exception_with_error_page(e)

        token = calendar_service.get_calendar_token(resource_type=url_res_type,
                                                    identifier=teacher.teacher_id,
                                                    semester=url_semester)

    ics_url = url_for('calendar.ics_download', calendar_token=token, _external=True)
    ics_webcal = ics_url.replace('https', 'webcal').replace('http', 'webcal')

    return render_template('calendarSubscribe.html',
                           ics_url=ics_url,
                           ics_webcal=ics_webcal,
                           android_client_url=app.config['ANDROID_CLIENT_URL'])


@cal_blueprint.route('/calendar/ics/<calendar_token>.ics')
@disallow_in_maintenance
def ics_download(calendar_token: str):
    """
    iCalendar ics 文件下载

    2019-8-25 改为预先缓存文件而非每次动态生成，降低 CPU 压力。如果一小时内两次访问则强刷缓存。
    """
    if not is_valid_uuid(calendar_token):
        return 'invalid calendar token', 404

    result = calendar_service.find_calendar_token(token=calendar_token)
    if not result:
        return 'invalid calendar token', 404
    calendar_service.use_calendar_token(calendar_token)

    return send_from_directory(calendar_dir(),
                               calendar_service.generate_ics_file(result["type"], result["identifier"], result["semester"]),
                               as_attachment=True,
                               mimetype='text/calendar')


@cal_blueprint.route('/calendar/ics/_androidClient/<identifier>')
@disallow_in_maintenance
def android_client_get_semester(identifier):
    """android client get a student or teacher's semesters
    """
    try:
        search_result = entity_service.search(identifier)
    except Exception as e:
        return handle_exception_with_error_page(e)

    if len(search_result.students) == 1:
        return jsonify({'type': 'student',
                        'sid': search_result.students[0].student_id_encoded,
                        'semesters': search_result.students[0].semesters})
    if len(search_result.teachers) == 1:
        return jsonify({'type': 'teacher',
                        'tid': search_result.teachers[0].teacher_id_encoded,
                        'semesters': search_result.teachers[0].semesters})
    return "Bad request (got multiple people)", 400


@cal_blueprint.route('/calendar/ics/_androidClient/<resource_type>/<identifier>/<semester>')
@disallow_in_maintenance
def android_client_get_ics(resource_type, identifier, semester):
    """
    android client get a student or teacher's ics file

    If the student does not have privacy mode, anyone can use student number to subscribe his calendar.
    If the privacy mode is on and there is no HTTP basic authentication, return a 401(unauthorized)
    status code and the Android client ask user for password to try again.
    """
    # 检查 URL 参数
    try:
        res_type, res_id = decrypt(identifier)
    except ValueError:
        return "Invalid identifier", 400
    if resource_type not in ('student', 'teacher') or resource_type != res_type:
        return "Unknown resource type", 400

    if resource_type == 'teacher':
        try:
            teacher = entity_service.get_teacher_timetable(res_id, semester)
        except Exception as e:
            return handle_exception_with_error_page(e)

        cal_token = calendar_service.get_calendar_token(resource_type=resource_type,
                                                        identifier=teacher.teacher_id,
                                                        semester=semester)
        return redirect(url_for('calendar.ics_download', calendar_token=cal_token))
    else:  # student
        try:
            student = entity_service.get_student_timetable(res_id, semester)
        except Exception as e:
            return handle_exception_with_error_page(e)

        with tracer.trace('get_privacy_settings'):
            privacy_level = user_service.get_privacy_level(student.student_id)

        # get authorization from HTTP header and verify password if privacy is on
        if privacy_level != 0:
            if not request.authorization:
                return "Unauthorized (privacy on)", 401
            username, password = request.authorization
            if not user_service.check_password(username, password):
                return "Unauthorized (password wrong)", 401
            if student.student_id != username:
                return "Unauthorized (username mismatch)", 401

        cal_token = calendar_service.get_calendar_token(resource_type=resource_type,
                                                        identifier=student.student_id,
                                                        semester=semester)
        return redirect(url_for('calendar.ics_download', calendar_token=cal_token))


@cal_blueprint.route('/<student_id>-<semester_str>.ics')
@disallow_in_maintenance
def legacy_get_ics(student_id, semester_str):
    """
    早期 iCalendar 订阅端点，出于兼容性考虑保留，仅支持未设定隐私等级的学生，其他情况使用新的日历订阅令牌获得 ics 文件。
    """
    # fix parameters
    place = student_id.find('-')
    semester_str = student_id[place + 1:len(student_id)] + '-' + semester_str
    student_id = student_id[:place]

    semester = Semester(semester_str)

    search_result = entity_service.search(student_id)

    if len(search_result.students) != 1:
        # bad request
        return abort(400)

    if semester.to_str() not in search_result.students[0].semesters:
        return abort(400)

    with tracer.trace('get_privacy_settings'):
        privacy_settings = user_service.get_privacy_level(search_result.students[0].student_id)

    if privacy_settings != 0:
        # force user to get a calendar token when the user is privacy-protected but accessed through legacy interface
        return "Visit {} to get your calendar".format(url_for("main.main", _external=True)), 401
    else:
        token = calendar_service.get_calendar_token(resource_type="student",
                                                    identifier=search_result.students[0].student_id,
                                                    semester=semester.to_str())
        return redirect(url_for('calendar.ics_download', calendar_token=token))

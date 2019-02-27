"""
日历相关函数
"""
import elasticapm
from flask import Blueprint

from everyclass.server.db.dao import ResourceType
from everyclass.server.utils.decorators import disallow_in_maintenance

cal_blueprint = Blueprint('calendar', __name__)


@cal_blueprint.route('/calendar/<string:resource_type>/<resource_identifier>/<string:url_semester>')
@disallow_in_maintenance
def cal_page(resource_type: str, resource_identifier: str, url_semester: str):
    """课表导出页面视图函数"""
    from flask import current_app as app, render_template, url_for, flash, redirect

    from everyclass.server.utils.rpc import HttpRpc
    from everyclass.server.db.dao import CalendarTokenDAO

    if resource_type not in ('student', 'teacher'):
        flash('请求异常')
        return redirect(url_for('main.main'))
    resource_type = ResourceType(resource_type)

    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = HttpRpc.call_with_error_page('{}/v1/{}/{}/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                          resource_type,
                                                                          resource_identifier,
                                                                          url_semester))
        if isinstance(rpc_result, str):
            return rpc_result

    token = CalendarTokenDAO.get_or_set_calendar_token(resource_type=resource_type,
                                                       identifier=resource_identifier,
                                                       semester=url_semester)

    ics_url = url_for('calendar.ics_download', calendar_token=token, _external=True)
    ics_webcal = ics_url.replace('https', 'webcal').replace('http', 'webcal')

    return render_template('calendarSubscribe.html',
                           ics_url=ics_url,
                           ics_webcal=ics_webcal,
                           android_client_url=app.config['ANDROID_CLIENT_URL'])


@cal_blueprint.route('/calendar/ics/<calendar_token>.ics')
@disallow_in_maintenance
def ics_download(calendar_token):
    """
    iCalendar ics file download

    因为课表会更新，所以 ics 文件只能在这里动态生成，不能在日历订阅页面就生成
    """
    from flask import send_from_directory, current_app
    from everyclass.server.db.dao import CalendarTokenDAO
    from everyclass.server.db.model import Semester
    from everyclass.server.calendar import ics_generator
    from everyclass.server.utils.rpc import HttpRpc
    from everyclass.server.utils import teacher_list_fix
    from everyclass.server.utils import teacher_list_to_str
    from everyclass.server.utils import lesson_string_to_dict

    result = CalendarTokenDAO.find_calendar_token(token=calendar_token)
    if not result:
        return 'invalid calendar token', 404

    with elasticapm.capture_span('rpc_find_people'):
        rpc_result = HttpRpc.call_with_error_page('{}/v1/{}/{}/{}'.format(current_app.config['API_SERVER_BASE_URL'],
                                                                          result['type'],
                                                                          result['sid'] if result['type'] == 'student'
                                                                          else result['tid'],
                                                                          result['semester']),
                                                  params={'week_string': 'true'})
        if isinstance(rpc_result, str):
            return rpc_result
        api_response = rpc_result

    with elasticapm.capture_span('process_rpc_result'):
        semester = Semester(result['semester'])

        courses = dict()
        for each_class in api_response['course']:
            day, time = lesson_string_to_dict(each_class['lesson'])
            if (day, time) not in courses:
                courses[(day, time)] = list()
            courses[(day, time)].append(dict(name=each_class['name'],
                                             teacher=teacher_list_to_str(teacher_list_fix(each_class['teacher'])),
                                             week=each_class['week'],
                                             week_string=each_class['week_string'],
                                             classroom=each_class['room'],
                                             classroom_id=each_class['rid'],
                                             cid=each_class['cid']))

    ics_generator.generate(student_name=api_response['name'],
                           courses=courses,
                           semester_string=semester.to_str(simplify=True),
                           semester=semester.to_tuple(),
                           ics_token=calendar_token
                           )

    return send_from_directory("../../calendar_files", calendar_token + ".ics",
                               as_attachment=True,
                               mimetype='text/calendar')


@cal_blueprint.route('/calendar/ics/_androidClient/<identifier>')
@disallow_in_maintenance
def android_client_get_semester(identifier):
    """android client get a student or teacher's semesters
    """
    from flask import current_app as app, jsonify
    from everyclass.server.utils.rpc import HttpRpc

    with elasticapm.capture_span('rpc_search'):
        rpc_result = HttpRpc.call_with_handle_message('{}/v1/search/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                               identifier))
        if isinstance(rpc_result, tuple):
            return rpc_result
        api_response = rpc_result

    if len(api_response['student']) == 1:
        return jsonify({'type'     : 'student',
                        'sid'      : api_response['student'][0]['sid'],
                        'semesters': sorted(api_response['student'][0]['semester'])})
    if len(api_response['teacher']) == 1:
        return jsonify({'type'     : 'teacher',
                        'tid'      : api_response['teacher'][0]['tid'],
                        'semesters': sorted(api_response['teacher'][0]['semester'])})
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
    from flask import current_app as app, redirect, url_for, request

    from everyclass.server.utils.rpc import HttpRpc
    from everyclass.server.db.dao import PrivacySettingsDAO, CalendarTokenDAO, UserDAO

    if resource_type not in ('student', 'teacher'):
        return "Unknown resource type", 400

    with elasticapm.capture_span('rpc_search'):
        rpc_result = HttpRpc.call_with_handle_message('{}/v1/{}/{}/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                              resource_type,
                                                                              identifier,
                                                                              semester))
        if isinstance(rpc_result, tuple):
            return rpc_result
        api_response = rpc_result

    if resource_type == 'teacher':
        cal_token = CalendarTokenDAO.get_or_set_calendar_token(resource_type=resource_type,
                                                               identifier=identifier,
                                                               semester=semester)
        return redirect(url_for('calendar.ics_download', calendar_token=cal_token))
    else:
        # student
        with elasticapm.capture_span('get_privacy_settings'):
            privacy_level = PrivacySettingsDAO.get_level(api_response['sid'])

        # get authorization from HTTP header and verify password if privacy is on
        if privacy_level != 0:
            if not request.authorization:
                return "Unauthorized (privacy on)", 401
            username, password = request.authorization
            if not UserDAO.check_password(username, password):
                return "Unauthorized (password wrong)", 401
            if api_response['sid'] != username:
                return "Unauthorized (username mismatch)", 401

        cal_token = CalendarTokenDAO.get_or_set_calendar_token(resource_type=resource_type,
                                                               identifier=identifier,
                                                               semester=semester)
        return redirect(url_for('calendar.ics_download', calendar_token=cal_token))


@cal_blueprint.route('/<student_id>-<semester_str>.ics')
@disallow_in_maintenance
def legacy_get_ics(student_id, semester_str):
    """
    legacy iCalendar endpoint

    query the student first, if the student is not privacy protected, redirect to new ics. else return 401.

    this route is bad. however, many users have already been using it. breaking experience is bad. so we have
    to keep the route here for now. and (maybe) remove it in the future.
    """
    from flask import current_app as app, abort, redirect, url_for

    from everyclass.server.db.dao import PrivacySettingsDAO, CalendarTokenDAO
    from everyclass.server.utils.rpc import HttpRpc
    from everyclass.server.db.model import Semester

    # fix parameters
    place = student_id.find('-')
    semester_str = student_id[place + 1:len(student_id)] + '-' + semester_str
    student_id = student_id[:place]

    semester = Semester(semester_str)

    with elasticapm.capture_span('rpc_search'):
        rpc_result = HttpRpc.call_with_error_page('{}/v1/search/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                           student_id))
        if isinstance(rpc_result, str):
            return rpc_result
        api_response = rpc_result

    if len(api_response['student']) != 1:
        # bad request
        return abort(400)

    if semester.to_str() not in api_response['student'][0]['semester']:
        return abort(400)

    with elasticapm.capture_span('get_privacy_settings'):
        privacy_settings = PrivacySettingsDAO.get_level(api_response['student'][0]['sid_orig'])

    if privacy_settings != 0:
        # force user to get a calendar token when the user is privacy-protected but accessed through legacy interface
        return "Visit {} to get your calendar".format(url_for("main.main")), 401
    else:
        token = CalendarTokenDAO.get_or_set_calendar_token(resource_type=ResourceType.student,
                                                           identifier=api_response['student'][0]['sid'],
                                                           semester=semester.to_str())
        return redirect(url_for('calendar.ics_download', calendar_token=token))

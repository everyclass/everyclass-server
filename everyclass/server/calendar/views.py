"""
日历相关函数
"""

import elasticapm
from flask import Blueprint

cal_blueprint = Blueprint('calendar', __name__)


@cal_blueprint.route('/calendar/<string:url_sid>/<string:url_semester>')
def cal_page(url_sid, url_semester):
    """课表导出页面视图函数"""
    from werkzeug.wrappers import Response
    from flask import current_app as app, render_template

    from everyclass.server.utils.rpc import HttpRpc
    from everyclass.server.db.dao import insert_calendar_token, find_calendar_token

    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = HttpRpc.call_with_error_handle('{}/v1/student/{}/{}'.format(app.config['API_SERVER'],
                                                                                 url_sid,
                                                                                 url_semester))
        if isinstance(rpc_result, Response):
            return rpc_result

    token = find_calendar_token(sid=url_sid, semester=url_semester)
    if not token:
        token = insert_calendar_token(sid=url_sid, semester=url_semester)
    else:
        token = token['token']

    return render_template('calendar_subscribe.html',
                           calendar_token=token)


@cal_blueprint.route('/calendar/ics/<calendar_token>.ics')
def ics_download(calendar_token):
    """
    iCalendar ics file download

    因为课表会更新，所以 ics 文件只能在这里动态生成，不能在日历订阅页面就生成
    """
    from werkzeug.wrappers import Response
    from flask import send_from_directory, current_app
    from everyclass.server.db.dao import find_calendar_token
    from everyclass.server.db.model import Semester
    from everyclass.server.calendar import ics_generator
    from everyclass.server.utils.rpc import HttpRpc
    from everyclass.server.tools import lesson_string_to_dict, teacher_list_fix, teacher_list_to_str

    # todo ics download
    result = find_calendar_token(token=calendar_token)
    if not result:
        return 'invalid calendar token', 404

    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = HttpRpc.call_with_error_handle('{}/v1/student/{}/{}'.format(current_app.config['API_SERVER'],
                                                                                 result['sid'],
                                                                                 result['semester']),
                                                    params={'week_string': 'true'})
        if isinstance(rpc_result, Response):
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


@cal_blueprint.route('/calendar/ics/_androidClient/<url_xh>.ics')
def android_client_get_ics(url_xh):
    """
    android client get ics

    If the student does not have privacy mode, anyone can use student number to subscribe his calendar.
    If the privacy mode is on and there is no HTTP basic authentication, return a 401(unauthorized)
    status code and the Android client ask user for password to try again.
    """
    pass


@cal_blueprint.route('/<student_id>-<semester_str>.ics')
def get_ics(student_id, semester_str):
    """
    legacy iCalendar endpoint

    query the student first, if the student is not privacy protected, redirect to new ics. else return 401.
    """
    from werkzeug.wrappers import Response
    from flask import current_app as app, abort, redirect, url_for

    from everyclass.server.db.dao import get_privacy_settings, find_calendar_token, insert_calendar_token
    from everyclass.server.utils.rpc import HttpRpc
    from everyclass.server.db.model import Semester

    # fix parameters
    place = student_id.find('-')
    semester_str = student_id[place + 1:len(student_id)] + '-' + semester_str
    student_id = student_id[:place]

    semester = Semester(semester_str)

    with elasticapm.capture_span('rpc_search'):
        rpc_result = HttpRpc.call_with_error_handle('{}/v1/search/{}'.format(app.config['API_SERVER'],
                                                                             student_id))
        if isinstance(rpc_result, Response):
            return rpc_result
        api_response = rpc_result

    if len(api_response['student']) != 1:
        # bad request
        return abort(400)

    if semester.to_str() not in api_response['student'][0]['semester']:
        return abort(400)

    with elasticapm.capture_span('get_privacy_settings', span_type='db.mysql'):
        # todo this need to be replaced with real student id here
        privacy_settings = get_privacy_settings(api_response['student'][0]['sid'])
        # legacy privacy setting, for disable a user's all operations
        if "show_table_on_page" in privacy_settings:
            return abort(401)

    token_result = find_calendar_token(sid=api_response['student'][0]['sid'], semester=semester.to_str())
    if not token_result:
        token = insert_calendar_token(sid=api_response['student'][0]['sid'], semester=semester.to_str())
    else:
        token = token_result['token']
    return redirect(url_for('calendar.ics_download', calendar_token=token))

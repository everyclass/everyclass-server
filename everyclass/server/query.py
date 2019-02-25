"""
查询相关函数
"""
import elasticapm
from flask import Blueprint, current_app as app, escape, flash, redirect, render_template, request, session, url_for

from everyclass.server import logger
from everyclass.server.db.model import Student
from everyclass.server.utils import contains_chinese, disallow_in_maintenance

query_blueprint = Blueprint('query', __name__)


@query_blueprint.route('/query', methods=['GET', 'POST'])
@disallow_in_maintenance
def query():
    """
    All in one 搜索入口，可以查询学生、老师、教室，然后跳转到具体资源页面

    正常情况应该是 post 方法，但是也兼容 get 防止意外情况，提高用户体验

    埋点：
    - `query_resource_type`, 查询的资源类型: classroom, single_student, single_teacher, multiple_people, or not_exist.
    - `query_type`, 查询方式（姓名、学工号）: by_name, by_id, other
    """
    import re
    from everyclass.server.utils.rpc import HttpRpc

    # if under maintenance, return to maintenance.html
    if app.config["MAINTENANCE"]:
        return render_template("maintenance.html")

    # transform upper case xh to lower case(currently api-server does not support upper case xh)
    to_search = request.values.get('id')

    if not to_search:
        flash('请输入需要查询的姓名、学号、教工号或教室名称')
        return redirect(url_for('main.main'))

    if re.match('^[A-Za-z0-9]*$', request.values.get('id')):
        to_search = to_search.lower()

    # add ‘座‘ since many users may search classroom in new campus without '座' and api-server doesn't not support
    if to_search[0] in ('a', 'b', 'c', 'd') and len(to_search) <= 5:
        to_search = to_search[0] + '座' + to_search[1:]

    # call api-server to search
    with elasticapm.capture_span('rpc_search'):
        rpc_result = HttpRpc.call_with_error_page('{}/v1/search/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                           to_search.replace("/", "")))
        if isinstance(rpc_result, str):
            return rpc_result
        api_response = rpc_result

    # render different template for different resource types
    if len(api_response['room']) >= 1:
        # classroom
        # we will use service name to filter apm document first, so it's not required to add service name prefix here
        elasticapm.tag(query_resource_type='classroom')
        elasticapm.tag(query_type='by_name')
        api_response['room'][0]['semester'].sort()
        return redirect('/classroom/{}/{}'.format(api_response['room'][0]['rid'],
                                                  api_response['room'][0]['semester'][-1]))
    elif len(api_response['student']) == 1 and len(api_response['teacher']) == 0:
        # only one student
        elasticapm.tag(query_resource_type='single_student')
        if contains_chinese(to_search):
            elasticapm.tag(query_type='by_name')
        else:
            elasticapm.tag(query_type='by_id')
        if len(api_response['student'][0]['semester']) < 1:
            flash('没有可用学期')
            return redirect(url_for('main.main'))
        api_response['student'][0]['semester'].sort()
        return redirect('/student/{}/{}'.format(api_response['student'][0]['sid'],
                                                api_response['student'][0]['semester'][-1]))
    elif len(api_response['teacher']) == 1 and len(api_response['student']) == 0:
        # only one teacher
        elasticapm.tag(query_resource_type='single_teacher')
        if contains_chinese(to_search):
            elasticapm.tag(query_type='by_name')
        else:
            elasticapm.tag(query_type='by_id')
        if len(api_response['teacher'][0]['semester']) < 1:
            flash('没有可用学期')
            return redirect(url_for('main.main'))
        api_response['teacher'][0]['semester'].sort()
        return redirect('/teacher/{}/{}'.format(api_response['teacher'][0]['tid'],
                                                api_response['teacher'][0]['semester'][-1]))
    elif len(api_response['teacher']) >= 1 or len(api_response['student']) >= 1:
        # multiple students, multiple teachers, or mix of both
        elasticapm.tag(query_resource_type='multiple_people')
        if contains_chinese(to_search):
            elasticapm.tag(query_type='by_name')
        else:
            elasticapm.tag(query_type='by_id')
        return render_template('query/peopleWithSameName.html',
                               name=to_search,
                               students_count=len(api_response['student']),
                               students=api_response['student'],
                               teachers_count=len(api_response['teacher']),
                               teachers=api_response['teacher'])
    else:
        elasticapm.tag(query_resource_type='not_exist')
        elasticapm.tag(query_type='other')
        flash('没有找到任何有关 {} 的信息，如果你认为这不应该发生，请联系我们。'.format(escape(request.values.get('id'))))
        return redirect(url_for('main.main'))


@query_blueprint.route('/student/<string:url_sid>/<string:url_semester>')
@disallow_in_maintenance
def get_student(url_sid, url_semester):
    """学生查询"""
    from everyclass.server.db.dao import get_privacy_settings
    from everyclass.server.utils import lesson_string_to_dict
    from everyclass.server.utils import teacher_list_fix
    from everyclass.server.utils import semester_calculate
    from everyclass.server.utils.rpc import HttpRpc
    from everyclass.server.consts import SESSION_LAST_VIEWED_STUDENT

    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = HttpRpc.call_with_error_page('{}/v1/student/{}/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                               url_sid,
                                                                               url_semester),
                                                  params={'week_string': 'true', 'other_semester': 'true'})
        if isinstance(rpc_result, str):
            return rpc_result
        api_response = rpc_result

    with elasticapm.capture_span('process_rpc_result'):
        courses = dict()
        for each_class in api_response['course']:
            day, time = lesson_string_to_dict(each_class['lesson'])
            if (day, time) not in courses:
                courses[(day, time)] = list()
            courses[(day, time)].append(dict(name=each_class['name'],
                                             teacher=teacher_list_fix(each_class['teacher']),
                                             week=each_class['week_string'],
                                             classroom=each_class['room'],
                                             classroom_id=each_class['rid'],
                                             cid=each_class['cid']))

    # save sid_orig to session for verifying purpose
    session[SESSION_LAST_VIEWED_STUDENT] = Student(sid_orig=api_response['sid'], sid=url_sid, name=api_response['name'])

    empty_5, empty_6, empty_sat, empty_sun = _empty_column_check(courses)

    available_semesters = semester_calculate(url_semester, sorted(api_response['semester_list']))

    # 隐私设定
    # Available privacy settings: "show_table_on_page", "import_to_calender", "major"
    with elasticapm.capture_span('get_privacy_settings', span_type='db.mysql'):
        privacy_settings = get_privacy_settings(api_response['sid'])

    # privacy on
    if "show_table_on_page" in privacy_settings:
        return render_template('query/studentBlocked.html',
                               name=api_response['name'],
                               falculty=api_response['deputy'],
                               class_name=api_response['class'],
                               sid=url_sid,
                               available_semesters=available_semesters,
                               no_import_to_calender=True if "import_to_calender" in privacy_settings else False,
                               current_semester=url_semester)

    # privacy off
    return render_template('query/student.html',
                           name=api_response['name'],
                           falculty=api_response['deputy'],
                           class_name=api_response['class'],
                           sid=url_sid,
                           classes=courses,
                           empty_sat=empty_sat,
                           empty_sun=empty_sun,
                           empty_6=empty_6,
                           empty_5=empty_5,
                           available_semesters=available_semesters,
                           current_semester=url_semester)


@query_blueprint.route('/teacher/<string:url_tid>/<string:url_semester>')
@disallow_in_maintenance
def get_teacher(url_tid, url_semester):
    """老师查询"""
    from everyclass.server.utils import lesson_string_to_dict
    from everyclass.server.utils import semester_calculate
    from .utils.rpc import HttpRpc

    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = HttpRpc.call_with_error_page('{}/v1/teacher/{}/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                               url_tid,
                                                                               url_semester),
                                                  params={'week_string': 'true', 'other_semester': 'true'})
        if isinstance(rpc_result, str):
            return rpc_result
        api_response = rpc_result

    with elasticapm.capture_span('process_rpc_result'):
        courses = dict()
        for each_class in api_response['course']:
            day, time = lesson_string_to_dict(each_class['lesson'])
            if (day, time) not in courses:
                courses[(day, time)] = list()
            courses[(day, time)].append(dict(name=each_class['name'],
                                             week=each_class['week_string'],
                                             classroom=each_class['room'],
                                             classroom_id=each_class['rid'],
                                             cid=each_class['cid']))

    empty_5, empty_6, empty_sat, empty_sun = _empty_column_check(courses)

    available_semesters = semester_calculate(url_semester, sorted(api_response['semester_list']))

    return render_template('query/teacher.html',
                           name=api_response['name'],
                           falculty=api_response['unit'],
                           title=api_response['title'],
                           tid=url_tid,
                           classes=courses,
                           empty_sat=empty_sat,
                           empty_sun=empty_sun,
                           empty_6=empty_6,
                           empty_5=empty_5,
                           available_semesters=available_semesters,
                           current_semester=url_semester)


@query_blueprint.route('/classroom/<string:url_rid>/<string:url_semester>')
@disallow_in_maintenance
def get_classroom(url_rid, url_semester):
    """教室查询"""
    from everyclass.server.utils import lesson_string_to_dict
    from everyclass.server.utils import teacher_list_fix
    from everyclass.server.utils import semester_calculate
    from .utils.rpc import HttpRpc

    with elasticapm.capture_span('rpc_query_room'):
        rpc_result = HttpRpc.call_with_error_page('{}/v1/room/{}/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                            url_rid,
                                                                            url_semester),
                                                  params={'week_string': 'true', 'other_semester': 'true'})
        if isinstance(rpc_result, str):
            return rpc_result
        api_response = rpc_result

    if 'name' not in api_response:
        logger.info("Hit classroom 'name' KeyError temporary fix")
        flash("教务数据异常，暂时无法查询本教室。其他教室不受影响。")
        return redirect(url_for("main.main"))

    with elasticapm.capture_span('process_rpc_result'):
        courses = dict()
        for each_class in api_response['course']:
            day, time = lesson_string_to_dict(each_class['lesson'])
            if (day, time) not in courses:
                courses[(day, time)] = list()
            courses[(day, time)].append(dict(name=each_class['name'],
                                             week=each_class['week_string'],
                                             teacher=teacher_list_fix(each_class['teacher']),
                                             location=each_class['room'],
                                             cid=each_class['cid']))

    empty_5, empty_6, empty_sat, empty_sun = _empty_column_check(courses)

    available_semesters = semester_calculate(url_semester, sorted(api_response['semester_list']))

    return render_template('query/room.html',
                           name=api_response['name'],
                           campus=api_response['campus'],
                           building=api_response['building'],
                           rid=url_rid,
                           classes=courses,
                           empty_sat=empty_sat,
                           empty_sun=empty_sun,
                           empty_6=empty_6,
                           empty_5=empty_5,
                           available_semesters=available_semesters,
                           current_semester=url_semester)


@query_blueprint.route('/course/<string:url_cid>/<string:url_semester>')
@disallow_in_maintenance
def get_course(url_cid: str, url_semester: str):
    """课程查询"""

    from everyclass.server.utils import teacher_list_to_str
    from everyclass.server.utils import lesson_string_to_dict
    from everyclass.server.utils import get_time_chinese
    from everyclass.server.utils import get_day_chinese
    from everyclass.server.utils import teacher_list_fix
    from .utils.rpc import HttpRpc

    with elasticapm.capture_span('rpc_query_course'):
        rpc_result = HttpRpc.call_with_error_page('{}/v1/course/{}/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                              url_cid,
                                                                              url_semester),
                                                  params={'week_string': 'true'})
        if isinstance(rpc_result, str):
            return rpc_result
        api_response = rpc_result

    day, time = lesson_string_to_dict(api_response['lesson'])

    # student list
    students = list()
    for each in api_response['student']:
        students.append([each['name'], each['sid'], each['deputy'], each['class']])

    # 给“文化素质类”等加上“课”后缀
    if api_response['type'] and api_response['type'][-1] != '课':
        api_response['type'] = api_response['type'] + '课'

    # 合班名称为数字时不展示合班名称
    show_heban = True
    if api_response['class'].isdigit():
        show_heban = False

    return render_template('query/course.html',
                           course_name=api_response['name'],
                           course_day=get_day_chinese(day),
                           course_time=get_time_chinese(time),
                           study_hour=api_response['hour'],
                           show_heban=show_heban,
                           heban_name=api_response['class'],
                           course_type=api_response['type'],
                           week=api_response['week_string'],
                           room=api_response['room'],
                           course_teacher=teacher_list_to_str(teacher_list_fix(api_response['teacher'])),
                           students=students,
                           student_count=len(api_response['student']),
                           current_semester=url_semester
                           )


def _empty_column_check(courses: dict) -> (bool, bool, bool, bool):
    """检查是否周末和晚上有课，返回三个布尔值"""
    with elasticapm.capture_span('_empty_column_check'):
        # 空闲周末判断，考虑到大多数人周末都是没有课程的
        empty_sat = True
        for cls_time in range(1, 7):
            if (6, cls_time) in courses:
                empty_sat = False

        empty_sun = True
        for cls_time in range(1, 7):
            if (7, cls_time) in courses:
                empty_sun = False

        # 空闲课程判断，考虑到大多数人11-12节都是没有课程的
        empty_6 = True
        for cls_day in range(1, 8):
            if (cls_day, 6) in courses:
                empty_6 = False
        empty_5 = True
        for cls_day in range(1, 8):
            if (cls_day, 5) in courses:
                empty_5 = False
    return empty_5, empty_6, empty_sat, empty_sun

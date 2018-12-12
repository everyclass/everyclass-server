"""
查询相关函数
"""
import elasticapm
import gevent
import requests
from flask import Blueprint, current_app as app, escape, flash, redirect, render_template, request, session, url_for

from . import logger
from .exceptions import *

query_blueprint = Blueprint('query', __name__)


@query_blueprint.route('/query', methods=['GET', 'POST'])
def query():
    """
    All in one 搜索入口，可以查询学生、老师、教室，然后跳转到具体资源页面

    正常情况应该是 post 方法，但是也兼容 get 防止意外情况，提高用户体验

    埋点：
    - `query_resource_type`, 查询类型: classroom, single_student, single_teacher, people, or nothing.
    - `query_type`（原 `ec_query_method`）, 查询方式: by_student_name, by_student_id, by_teacher_name,
      by_teacher_id, by_room_name, other
    """
    from flask import current_app as app

    # if under maintenance, return to maintenance.html
    if app.config["MAINTENANCE"]:
        return render_template("maintenance.html")

    print('hello')
    logger.info('world')

    # call api-server to search
    with elasticapm.capture_span('rpc_search'):
        api_session = requests.sessions.session()
        try:
            with gevent.Timeout(5):
                api_response = api_session.get('{}/v1/_search/{}'.format(app.config['API_SERVER'],
                                                                         request.values.get('id').encode('utf-8'))
                                               )
            _handle_http_status_code(api_response)
            api_response = api_response.json()
        except RpcClientException as e:
            logger.error(repr(e))
            return _flash_and_redirect('请求错误')
        except RpcServerException as e:
            logger.error(repr(e))
            return _flash_and_redirect('服务器内部错误。已经通知管理员，抱歉引起不便。')
        except Exception as e:
            logger.error('RPC exception: {}'.format(repr(e)))
            return _flash_and_redirect('服务器内部错误。已经通知管理员，抱歉引起不便。')

    # render different template for different resource types
    if 'room' in api_response:
        # classroom
        # we will use service name to filter apm document first, so it's not required to add service name prefix here
        elasticapm.tag(query_resource_type='classroom')
        return redirect('/classroom?rid={}'.format(api_response['room'][0]['rid']))
    elif 'student' in api_response and len(api_response['student']) == 1 and 'teacher' not in api_response:
        # only one student
        elasticapm.tag(query_resource_type='single_student')
        if len(api_response['student'][0]['semester']) < 1:
            flash('没有可用学期')
            return redirect(url_for('main.main'))
        return redirect('/student/{}/{}'.format(api_response['student'][0]['sid'],
                                                api_response['student'][0]['semester'][-1]))
    elif 'teacher' in api_response and len(api_response['teacher']) == 1 and 'student' not in api_response:
        # only one teacher
        elasticapm.tag(query_resource_type='single_teacher')
        return redirect('/teacher?rid={}&semester={}'.format(api_response['teacher'][0]['tid'],
                                                             api_response['teacher'][0]['semester'][-1]))
    elif 'teacher' in api_response or 'student' in api_response:
        # multiple students, multiple teachers, or mix of both
        elasticapm.tag(query_resource_type='people')
        return render_template('query_same_name.html',
                               students=api_response['student'],
                               teachers=api_response['teacher'])
    else:
        elasticapm.tag(query_resource_type='nothing')
        flash('没有找到任何有关 %s 的信息，如果你认为这不应该发生，请联系我们。'.format(escape(request.values.get('id'))))
        return url_for('main.main')


@query_blueprint.route('/student/<string:url_sid>/<string:url_semester>')
def get_student(url_sid, url_semester):
    """学生查询"""
    from everyclass.server.db.dao import get_privacy_settings
    from everyclass.server.tools import lesson_string_to_dict, teacher_list_to_str

    with elasticapm.capture_span('rpc_query_student'):
        api_session = requests.sessions.session()
        api_response = api_session.get('{}/v1/student/{}/{}'.format(app.config['API_SERVER'],
                                                                    url_sid.encode('utf-8'),
                                                                    url_semester)
                                       , params={'week_string': 'true'})
        _handle_http_status_code(api_response)
        api_response = api_response.json()

    with elasticapm.capture_span('process_rpc_result'):
        student_classes = dict()
        for each_class in api_response['course']:
            day, time = lesson_string_to_dict(each_class['lesson'])
            if (day, time) not in student_classes:
                student_classes[(day, time)] = list()
            student_classes[(day, time)].append(dict(name=each_class['name'],
                                                     teacher=teacher_list_to_str(each_class['teacher']),
                                                     duration='',
                                                     week=each_class['week_string'],
                                                     location=each_class['room'],
                                                     id=each_class['cid']))

    with elasticapm.capture_span('empty_column_minify'):
        # 空闲周末判断，考虑到大多数人周末都是没有课程的
        empty_weekend = True
        for cls_time in range(1, 7):
            for cls_day in range(6, 8):
                if (cls_day, cls_time) in student_classes:
                    empty_weekend = False

        # 空闲课程判断，考虑到大多数人11-12节都是没有课程的
        empty_6 = True
        for cls_day in range(1, 8):
            if (cls_day, 6) in student_classes:
                empty_6 = False
        empty_5 = True
        for cls_day in range(1, 8):
            if (cls_day, 5) in student_classes:
                empty_5 = False

    # available_semesters 为当前学生所能选择的学期，是一个list。
    # 当中每一项又是一个包含两项的list，第一项为学期string，第二项为True/False表示是否为当前学期。
    with elasticapm.capture_span('semester_calculate'):
        available_semesters = []

        for each_semester in api_response['semester']:
            if session['semester'] == each_semester:
                available_semesters.append([each_semester, True])
            else:
                available_semesters.append([each_semester, False])

    # 隐私设定
    # Available privacy settings: "show_table_on_page", "import_to_calender", "major"
    with elasticapm.capture_span('get_privacy_settings', span_type='db.mysql'):
        privacy_settings = get_privacy_settings(api_response['xh'])

    # privacy on
    if "show_table_on_page" in privacy_settings:
        return render_template('blocked.html',
                               name=api_response['name'],
                               falculty=api_response['deputy'],
                               class_name=api_response['klass'],
                               stu_id=api_response['xh'],
                               available_semesters=available_semesters,
                               no_import_to_calender=True if "import_to_calender" in privacy_settings else False,
                               current_semester=url_semester)

    # privacy off
    return render_template('query.html',
                           name=api_response['name'],
                           falculty=api_response['deputy'],
                           class_name=api_response['klass'],
                           stu_id=api_response['xh'],
                           classes=student_classes,
                           empty_wkend=empty_weekend,
                           empty_6=empty_6,
                           empty_5=empty_5,
                           available_semesters=available_semesters,
                           current_semester=url_semester)


@query_blueprint.route('/course/<string:url_cid>/<string:url_semester>')
def get_course(url_cid: str, url_semester: str):
    """课程查询"""
    from flask import request, render_template

    from everyclass.server.tools import get_time_chinese, get_day_chinese
    from everyclass.server.db.dao import get_students_in_class

    with elasticapm.capture_span('rpc_query_course'):
        api_session = requests.sessions.session()
        api_response = api_session.get('{}/v1/course/{}/{}'.format(app.config['API_SERVER'],
                                                                   url_cid,
                                                                   url_semester)
                                       )
        _handle_http_status_code(api_response)
        api_response = api_response.json()

    # 默认不显示学号，加入 show_id 参数显示
    if request.values.get('show_id') and request.values.get('show_id') == 'true':
        show_id = True
    else:
        show_id = False

    # 获取选了这门课的学生信息
    class_name, class_day, class_time, class_teacher, students_info = get_students_in_class(
        request.values.get('class_id', None))
    return render_template('classmate.html',
                           class_name=class_name,
                           class_day=get_day_chinese(class_day),
                           class_time=get_time_chinese(class_time),
                           class_teacher=class_teacher,
                           students=students_info,
                           student_count=len(students_info),
                           show_id=show_id)


def _handle_http_status_code(response: requests.Response):
    """
    check HTTP RPC status code and raise exception if it's 4xx or 5xx

    :param response: a `Response` object
    """
    status_code = response.status_code
    if status_code >= 500:
        # server internal error
        raise RpcServerException(response.text)
    if 400 <= status_code < 500:
        # bad request
        raise RpcClientException(response.text)


def _flash_and_redirect(info: str):
    """flash message and return to main page"""
    flash(info)
    return redirect(url_for('main.main'))

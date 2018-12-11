"""
查询相关函数
"""
import elasticapm
import requests
from flask import Blueprint, escape, flash, redirect, render_template, request, session, url_for

from . import logger

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

    # call api-server to search
    with elasticapm.capture_span('rpc_search'):
        api_session = requests.sessions.session()
        api_response = api_session.get('{}/v1/_search/{}'.format(app.config['API_SERVER'],
                                                                 request.values.get('id').encode('utf-8'))
                                       )
        api_response = api_response.json()

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
    from flask import current_app as app

    from everyclass.server.tools import is_chinese_char
    from everyclass.server.exceptions import NoStudentException, IllegalSemesterException
    from everyclass.server.db.model import Semester
    from everyclass.server.db.dao import faculty_lookup, class_lookup, get_classes_for_student, get_privacy_settings, \
        get_my_semesters, check_if_stu_exist, get_students_by_name

    api_session = requests.sessions.session()
    api_response = api_session.get('{}/v1/student/{}/{}'.format(app.config['API_SERVER'],
                                                                url_sid.encode('utf-8'),
                                                                url_semester)
                                   )
    api_response = api_response.json()

    # 如 URL 中有 id 参数，判断是姓名还是学号，然后赋学号给student_id
    if request.values.get('id'):
        id_or_name = request.values.get('id')

        # 首末均为中文,判断为人名
        if is_chinese_char(id_or_name[0:1]) and is_chinese_char(id_or_name[-1:]):

            with elasticapm.capture_span('get_students_by_name', span_type='db.mysql'):
                students = get_students_by_name(id_or_name)
            if len(students) > 1:
                # 查询到多个同名，进入选择界面
                with elasticapm.capture_span('same_name_lookup', span_type='db.mysql'):
                    students_list = list()
                    for each_student in students:
                        students_list.append([each_student[0],
                                              each_student[1],
                                              faculty_lookup(each_student[1]),
                                              class_lookup(each_student[1])])
                return render_template("query_same_name.html", count=len(students_list), student_info=students_list)
            elif len(students) == 1:
                # 仅能查询到一个人，则赋值学号
                student_id = students[0][1]
            else:
                # 查无此人
                elasticapm.tag(ec_query_not_found=True)
                return _no_student_handle(id_or_name)

        # id 不为中文，则为学号
        else:
            # 学号查询打点
            elasticapm.tag(ec_query_method='by_id')
            student_id = request.values.get('id')

            # 判断学号是否有效
            if not check_if_stu_exist(student_id):
                elasticapm.tag(ec_query_not_found=True)
                return _no_student_handle(student_id)

        # 写入 session 的学号一定有效
        session['stu_id'] = student_id

    # url 中没有 id 参数但 session 中有
    elif session.get('stu_id', None):
        elasticapm.tag(ec_query_method='by_session')
        student_id = session['stu_id']

    # 既没有 id 参数也没有 session，无法知道需要查询谁的课表，返回主页
    else:
        elasticapm.tag(ec_query_method='exception')
        return redirect(url_for('main.main'))

    # 查询学生本人的可用学期
    with elasticapm.capture_span('get_semesters', span_type='db.mysql'):
        my_available_semesters, student_name = get_my_semesters(student_id)

    # 如果没有学期，则直接返回
    if not my_available_semesters:
        logger.warning('Not any semester in ec_student', stack=True)
        return _no_student_handle()

    # 如URL参数中包含学期，判断有效性后更新 session
    if request.values.get('semester'):
        try:
            sem = Semester(request.values.get('semester'))
            if sem in my_available_semesters:
                session['semester'] = sem.to_tuple()
                if app.config['DEBUG']:
                    print('[query.query] updated session semester to', Semester(session['semester']).to_str())

        # 用户指定的学期格式不合法
        except IllegalSemesterException:
            if app.config['DEBUG']:
                print('[query.query] IllegalSemesterException handled.' + Semester(session['semester']).to_str())
            session['semester'] = my_available_semesters[-1].to_tuple()

    # 如果 session 中无学期或学期无效，回落到本人可用最新学期
    # session 中学期使用 tuple 保存，因为 Semester 对象无法被序列化
    url_semester = session.get('semester', None)
    if not url_semester or Semester(url_semester) not in my_available_semesters:
        session['semester'] = my_available_semesters[-1].to_tuple()

    try:
        with elasticapm.capture_span('get_courses', span_type='db.mysql'):
            student_classes = get_classes_for_student(student_id=student_id, sem=Semester(session['semester']))
    except NoStudentException:
        return _no_student_handle(student_id)
    else:
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

            for each_semester in my_available_semesters:
                if session['semester'] == each_semester:
                    available_semesters.append([each_semester, True])
                else:
                    available_semesters.append([each_semester, False])

        # 隐私设定
        # Available privacy settings: "show_table_on_page", "import_to_calender", "major"
        with elasticapm.capture_span('get_privacy_settings', span_type='db.mysql'):
            privacy_settings = get_privacy_settings(student_id)

        # 获得所在学院和班级
        with elasticapm.capture_span('get_faculty_and_class', span_type='db.mysql'):
            faculty = faculty_lookup(student_id)
            class_name = class_lookup(student_id)

        # privacy on
        if "show_table_on_page" in privacy_settings:
            return render_template('blocked.html',
                                   name=student_name,
                                   falculty=faculty,
                                   class_name=class_name,
                                   stu_id=student_id,
                                   available_semesters=available_semesters,
                                   no_import_to_calender=True if "import_to_calender" in privacy_settings else False)

        # privacy off
        return render_template('query.html',
                               name=student_name,
                               falculty=faculty,
                               class_name=class_name,
                               stu_id=student_id,
                               classes=student_classes,
                               empty_wkend=empty_weekend,
                               empty_6=empty_6,
                               empty_5=empty_5,
                               available_semesters=available_semesters)


@query_blueprint.route('/classmates')
def get_classmates():
    """同学名单查询视图函数"""
    from flask import request, render_template, session, redirect, url_for

    from everyclass.server.tools import get_time_chinese, get_day_chinese
    from everyclass.server.db.dao import get_students_in_class

    # 如果 session stu_id 不存在则回到首页
    if not session.get('stu_id', None):
        return redirect(url_for('main.main'))

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


def _no_student_handle(stu_identifier=None):
    """
    flash a waring telling user that the identifier inputted is not found in database.

    :param stu_identifier: student id or name
    :return: none
    """
    from flask import escape, redirect, url_for
    if stu_identifier:
        flash('没有在数据库中找到你哦。是不是输错了？你刚刚输入的是%s。如果你输入正确且处于正常入学状态，请联系我们更新数据。' % escape(stu_identifier))
    else:
        flash('没有在数据库中找到你哦。如果你输入正确且处于正常入学状态，请联系我们更新数据。')
    return redirect(url_for('main.main'))

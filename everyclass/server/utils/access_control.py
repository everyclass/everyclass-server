from typing import Optional, Tuple

import elasticapm
from flask import render_template, session

from everyclass.server.consts import SESSION_CURRENT_USER, SESSION_LAST_VIEWED_STUDENT
from everyclass.server.db.dao import PrivacySettings, VisitTrack
from everyclass.server.rpc.api_server import StudentTimetableResult


def check_permission(student: StudentTimetableResult) -> Tuple[bool, Optional[str]]:
    """
    检查当前登录的用户是否有权限访问此学生

    :param student: 被访问的学生
    :return: 第一个返回值为布尔类型，True 标识可以访问，False 表示没有权限访问。第二个返回值为没有权限访问时需要返回的模板
    """
    with elasticapm.capture_span('get_privacy_settings'):
        privacy_level = PrivacySettings.get_level(student.student_id)

    # 仅自己可见、且未登录或登录用户非在查看的用户，拒绝访问
    if privacy_level == 2 and (not session.get(SESSION_CURRENT_USER, None) or
                               session[SESSION_CURRENT_USER].sid_orig != student.student_id):
        return False, render_template('query/studentBlocked.html',
                                      name=student.name,
                                      falculty=student.deputy,
                                      class_name=student.klass,
                                      level=2)
    # 实名互访
    if privacy_level == 1:
        # 未登录，要求登录
        if not session.get(SESSION_CURRENT_USER, None):
            return False, render_template('query/studentBlocked.html',
                                          name=student.name,
                                          falculty=student.deputy,
                                          class_name=student.klass,
                                          level=1)
        # 仅自己可见的用户访问实名互访的用户，拒绝，要求调整自己的权限
        if PrivacySettings.get_level(session[SESSION_CURRENT_USER].sid_orig) == 2:
            return False, render_template('query/studentBlocked.html',
                                          name=student.name,
                                          falculty=student.deputy,
                                          class_name=student.klass,
                                          level=3)

    # 公开或实名互访模式、已登录、不是自己访问自己，则留下轨迹
    if privacy_level != 2 and \
            session.get(SESSION_CURRENT_USER, None) and \
            session[SESSION_CURRENT_USER].sid_orig != session[SESSION_LAST_VIEWED_STUDENT].sid_orig:
        VisitTrack.update_track(host=student.student_id,
                                visitor=session[SESSION_CURRENT_USER])

    return True, None

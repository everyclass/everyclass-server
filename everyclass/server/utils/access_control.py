from typing import Optional, Tuple

from flask import render_template, session

from everyclass.rpc.entity import StudentTimetableResult
from everyclass.server.user import service as user_service
from everyclass.server.utils.pc_consts import SESSION_CURRENT_USER


def check_permission(student: StudentTimetableResult) -> Tuple[bool, Optional[str]]:
    """
    检查当前登录的用户是否有权限访问此学生

    :param student: 被访问的学生
    :return: 第一个返回值为布尔类型，True 标识可以访问，False 表示没有权限访问。第二个返回值为没有权限访问时需要返回的模板
    """

    try:
        can = user_service.has_access(student.student_id,
                                      session.get(SESSION_CURRENT_USER).identifier if session.get(SESSION_CURRENT_USER, None) else None)
    except user_service.LoginRequired:
        return False, render_template('query/studentBlocked.html',
                                      name=student.name,
                                      falculty=student.deputy,
                                      class_name=student.klass,
                                      level=1)
    except user_service.PermissionAdjustRequired:
        return False, render_template('query/studentBlocked.html',
                                      name=student.name,
                                      falculty=student.deputy,
                                      class_name=student.klass,
                                      level=3)

    if not can:
        return False, render_template('query/studentBlocked.html',
                                      name=student.name,
                                      falculty=student.deputy,
                                      class_name=student.klass,
                                      level=2)

    return True, None

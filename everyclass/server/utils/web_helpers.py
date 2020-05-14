import functools
from typing import Text, Tuple, Optional

from flask import render_template, session, g

from everyclass.common.flask import plugin_available
from everyclass.rpc import RpcTimeout, RpcResourceNotFound, RpcBadRequest, RpcClientException, RpcServerNotAvailable, RpcServerException
from everyclass.rpc.entity import StudentTimetableResult
from everyclass.server import sentry, logger
from everyclass.server.user import service as user_service
from everyclass.server.user.exceptions import AlreadyRegisteredError, InvalidTokenError, PermissionAdjustRequired, LoginRequired
from everyclass.server.utils.config import get_config
from everyclass.server.utils.web_consts import MSG_400, SESSION_CURRENT_USER, MSG_NOT_LOGGED_IN


def disallow_in_maintenance(func):
    """
    a decorator for routes which should be unavailable in maintenance mode.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        config = get_config()
        if config.MAINTENANCE:
            return render_template('maintenance.html')
        return func(*args, **kwargs)

    return wrapped


def url_semester_check(func):
    """
    捕获 URL 中异常的 semester 值
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if len(kwargs["url_semester"]) > 11:
            return render_template('common/error.html', message=MSG_400)
        return func(*args, **kwargs)

    return wrapped


def login_required(func):
    """
    a decorator for routes which is only available for logged-in users.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if not session.get(SESSION_CURRENT_USER, None):
            return render_template('common/error.html', message=MSG_NOT_LOGGED_IN, action="login")
        return func(*args, **kwargs)

    return wrapped


def _error_page(message: str, sentry_capture: bool = False, log: str = None):
    """return a error page with a message. if sentry is available, tell user that they can report the problem."""
    sentry_param = {}
    if sentry_capture and plugin_available("sentry"):
        sentry.captureException()
        sentry_param.update({"event_id": g.sentry_event_id,
                             "public_dsn": sentry.client.get_public_dsn('https')
                             })
    if log:
        logger.info(log)
    return render_template('common/error.html', message=message, **sentry_param)


def handle_exception_with_error_page(e: Exception) -> Text:
    """处理抛出的异常，返回错误页。
    """
    from everyclass.server.utils.web_consts import MSG_TIMEOUT, MSG_404, MSG_400, MSG_INTERNAL_ERROR, MSG_503, MSG_ALREADY_REGISTERED, \
        MSG_TOKEN_INVALID

    if isinstance(e, AlreadyRegisteredError):
        return _error_page(MSG_ALREADY_REGISTERED)
    if isinstance(e, InvalidTokenError):
        return _error_page(MSG_TOKEN_INVALID)

    if isinstance(e, RpcTimeout):
        return _error_page(MSG_TIMEOUT, sentry_capture=True)
    elif isinstance(e, RpcResourceNotFound):
        return _error_page(MSG_404, sentry_capture=True)
    elif isinstance(e, RpcBadRequest):
        return _error_page(MSG_400,
                           log="Got bad request, upstream returned status code {} with message {}.".format(*e.args),
                           sentry_capture=True)
    elif isinstance(e, RpcClientException):
        return _error_page(MSG_400, sentry_capture=True)
    elif isinstance(e, RpcServerNotAvailable):
        return _error_page(MSG_503, sentry_capture=True)
    elif isinstance(e, RpcServerException):
        return _error_page(MSG_INTERNAL_ERROR, sentry_capture=True)
    else:
        return _error_page(MSG_INTERNAL_ERROR, sentry_capture=True)


def check_permission(student: StudentTimetableResult) -> Tuple[bool, Optional[str]]:
    """
    检查当前登录的用户是否有权限访问此学生

    :param student: 被访问的学生
    :return: 第一个返回值为布尔类型，True 标识可以访问，False 表示没有权限访问。第二个返回值为没有权限访问时需要返回的模板
    """

    try:
        can = user_service.has_access(student.student_id,
                                      session.get(SESSION_CURRENT_USER).identifier if session.get(SESSION_CURRENT_USER, None) else None)
    except LoginRequired:
        return False, render_template('entity/studentBlocked.html',
                                      name=student.name,
                                      falculty=student.deputy,
                                      class_name=student.klass,
                                      level=1)
    except PermissionAdjustRequired:
        return False, render_template('entity/studentBlocked.html',
                                      name=student.name,
                                      falculty=student.deputy,
                                      class_name=student.klass,
                                      level=3)

    if not can:
        return False, render_template('entity/studentBlocked.html',
                                      name=student.name,
                                      falculty=student.deputy,
                                      class_name=student.klass,
                                      level=2)

    return True, None

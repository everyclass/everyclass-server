import functools

from flask import render_template, session

from everyclass.server.config import get_config
from everyclass.server.consts import MSG_400, MSG_NOT_LOGGED_IN, SESSION_CURRENT_STUDENT


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
        if not session.get(SESSION_CURRENT_STUDENT, None):
            return render_template('common/error.html', message=MSG_NOT_LOGGED_IN, action="login")
        return func(*args, **kwargs)

    return wrapped

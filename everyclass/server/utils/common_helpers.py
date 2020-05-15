import os

from flask import session

from everyclass.server.utils.web_consts import SESSION_CURRENT_USER, SESSION_USER_SEQ


def plugin_available(plugin_name: str) -> bool:
    """
    check if a plugin (Sentry, apm, logstash) is available in the current environment.
    :return True if available else False
    """
    from everyclass.server.utils.config import get_config
    config = get_config()
    mode = os.environ.get("MODE", None)
    if mode:
        return mode.lower() in getattr(config, "{}_AVAILABLE_IN".format(plugin_name).upper())
    else:
        raise EnvironmentError("MODE not in environment variables")


UTYPE_USER = "user"
UTYPE_GUEST = "guest"


def get_ut_uid():
    """已登录用户获得学号，未登录用户获得user序列ID"""
    if SESSION_CURRENT_USER in session:
        return UTYPE_USER, session[SESSION_CURRENT_USER].identifier
    if SESSION_USER_SEQ in session:
        return UTYPE_GUEST, session[SESSION_USER_SEQ]
    raise NotImplementedError("user seq not exist in session")


def get_logged_in_uid():
    """获得当前已登录的用户ID，如果未登录返回None"""
    ut, uid = get_ut_uid()
    if ut == UTYPE_GUEST:
        return None
    else:
        return uid

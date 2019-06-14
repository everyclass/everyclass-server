import os
from dataclasses import fields
from typing import Dict, Text, Tuple

from flask import current_app, g, render_template

_logger = None
_sentry = None
_resource_id_encrypt = None


def init(logger=None, sentry=None, resource_id_encrypt_function=None):
    """初始化 everyclass.rpc 模块

    """
    global _logger, _sentry, _resource_id_encrypt

    if logger:
        _logger = logger
    if sentry:
        _sentry = sentry
    if resource_id_encrypt_function:
        _resource_id_encrypt = resource_id_encrypt_function


def plugin_available(plugin_name: str) -> bool:
    """
    check if a plugin (Sentry, apm, logstash) is available in the current environment.
    :return True if available else False
    """
    mode = os.environ.get("MODE", None)
    if mode:
        return mode.lower() in getattr(current_app.config, "{}_AVAILABLE_IN".format(plugin_name).upper())
    else:
        raise EnvironmentError("MODE not in environment variables")


def _return_string(status_code, string, sentry_capture=False, log=None):
    if sentry_capture and plugin_available("sentry"):
        _sentry.captureException()
    if log:
        _logger.info(log)
    return string, status_code


def _error_page(message: str, sentry_capture: bool = False, log: str = None):
    """return a error page with a message. if sentry is available, tell user that they can report the problem."""
    sentry_param = {}
    if sentry_capture and plugin_available("sentry"):
        _sentry.captureException()
        sentry_param.update({"event_id"  : g.sentry_event_id,
                             "public_dsn": _sentry.client.get_public_dsn('https')
                             })
    if log:
        _logger.info(log)
    return render_template('common/error.html', message=message, **sentry_param)


def handle_exception_with_error_page(e: Exception) -> Text:
    """处理抛出的异常，返回错误页。
    """
    from everyclass.server.consts import MSG_TIMEOUT, MSG_404, MSG_400, MSG_INTERNAL_ERROR, MSG_503

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


def handle_exception_with_message(e: Exception) -> Tuple:
    """处理抛出的异常，返回错误消息"""
    if isinstance(e, RpcTimeout):
        return _return_string(408, "Backend timeout", sentry_capture=True)
    elif isinstance(e, RpcResourceNotFound):
        return _return_string(404, "Resource not found", sentry_capture=True)
    elif isinstance(e, RpcBadRequest):
        return _return_string(400, "Bad request", sentry_capture=True)
    elif isinstance(e, RpcClientException):
        return _return_string(400, "Bad request", sentry_capture=True)
    elif isinstance(e, RpcServerException):
        return _return_string(500, "Server internal error", sentry_capture=True)
    else:
        return _return_string(500, "Server internal error", sentry_capture=True)


def ensure_slots(cls, dct: Dict):
    """移除 dataclass 中不存在的key，预防 dataclass 的 __init__ 中 unexpected argument 的发生。"""
    _names = [x.name for x in fields(cls)]
    _del = []
    for key in dct:
        if key not in _names:
            _del.append(key)
    for key in _del:
        del dct[key]  # delete unexpected keys
        from everyclass.rpc import _logger
        _logger.warn(
                "Unexpected field `{}` is removed when converting dict to dataclass `{}`".format(key, cls.__name__))
    return dct


class RpcException(ConnectionError):
    """HTTP 4xx or 5xx"""
    pass


class RpcTimeout(RpcException, TimeoutError):
    """timeout"""
    pass


class RpcClientException(RpcException):
    """HTTP 4xx"""
    pass


class RpcResourceNotFound(RpcClientException):
    """HTTP 404"""
    pass


class RpcBadRequest(RpcClientException):
    """HTTP 400"""
    pass


class RpcServerException(RpcException):
    """HTTP 5xx"""
    pass


class RpcServerNotAvailable(RpcServerException):
    """HTTP 503"""
    pass

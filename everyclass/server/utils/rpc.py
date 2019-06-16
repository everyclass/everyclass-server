from typing import Text

from flask import g, render_template

from everyclass.rpc import RpcBadRequest, RpcClientException, RpcResourceNotFound, RpcServerException, \
    RpcServerNotAvailable, RpcTimeout, plugin_available
from everyclass.server import logger, sentry


def _error_page(message: str, sentry_capture: bool = False, log: str = None):
    """return a error page with a message. if sentry is available, tell user that they can report the problem."""
    sentry_param = {}
    if sentry_capture and plugin_available("sentry"):
        sentry.captureException()
        sentry_param.update({"event_id"  : g.sentry_event_id,
                             "public_dsn": sentry.client.get_public_dsn('https')
                             })
    if log:
        logger.info(log)
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

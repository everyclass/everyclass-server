import gevent
import requests
from flask import flash, redirect, url_for

from everyclass.server import logger
from everyclass.server.exceptions import *


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


def http_rpc(url, params=None):
    api_session = requests.sessions.session()
    try:
        with gevent.Timeout(5):
            logger.debug('RPC GET {}'.format(url))
            api_response = api_session.get(url, params=params)
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
    return api_response

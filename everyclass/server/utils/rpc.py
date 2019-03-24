from typing import Dict, Tuple, Union

import gevent
import requests
from flask import g, render_template

from everyclass.server import logger, sentry
from everyclass.server.consts import MSG_400, MSG_404, MSG_INTERNAL_ERROR, MSG_TIMEOUT
from everyclass.server.exceptions import RpcBadRequestException, \
    RpcClientException, RpcResourceNotFoundException, RpcServerException, RpcTimeoutException
from everyclass.server.utils import plugin_available


class HttpRpc:
    @classmethod
    def _status_code_raise(cls, response: requests.Response) -> None:
        """
        raise exception if HTTP status code is 4xx or 5xx

        :param response: a `Response` object
        """
        status_code = response.status_code
        if status_code >= 500:
            raise RpcServerException(status_code, response.text)
        if 400 <= status_code < 500:
            if status_code == 404:
                raise RpcResourceNotFoundException(status_code, response.text)
            if status_code == 400:
                raise RpcBadRequestException(status_code, response.text)
            raise RpcClientException(status_code, response.text)

    @classmethod
    def _error_page(cls, message: str, sentry_capture: bool = False, log: str = None):
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

    @classmethod
    def _return_string(cls, status_code, string, sentry_capture=False, log=None):
        if sentry_capture and plugin_available("sentry"):
            sentry.captureException()
        if log:
            logger.info(log)
        return string, status_code

    @classmethod
    def call(cls, method: str, url: str, params=None, retry: bool = False, data=None) -> Dict:
        """call HTTP API. if server returns 4xx or 500 status code, raise exceptions.
        :param method: HTTP method. Support GET or POST at the moment.
        :param url: URL of the HTTP endpoint
        :param params: parameters when calling RPC
        :param retry: if set to True, will automatically retry
        :param data: json data along with the request
        """
        api_session = requests.sessions.session()
        trial_total = 5 if retry else 1
        trial = 0
        while trial < trial_total:
            try:
                logger.debug('RPC {} {}'.format(method, url))
                if method == 'GET':
                    api_response = api_session.get(url, params=params, json=data)
                elif method == 'POST':
                    api_response = api_session.post(url, params=params, json=data)
                else:
                    raise NotImplementedError("Unsupported HTTP method {}".format(method))
            except gevent.timeout.Timeout:
                trial += 1
                continue
            cls._status_code_raise(api_response)
            response_json = api_response.json()
            logger.debug('RPC result: {}'.format(response_json))
            return response_json
        raise RpcTimeoutException('Timeout when calling {}. Tried {} time(s).'.format(url, trial_total))

    @classmethod
    def call_with_error_page(cls, url: str, params=None, retry: bool = False,
                             data=None, method: str = 'GET') -> Union[Dict, str]:
        """调用 API 并处理抛出的异常。如有异常，跳转到错误页。
        """
        try:
            api_response = cls.call(method, url, params=params, retry=retry, data=data)
        except RpcTimeoutException:
            return cls._error_page(MSG_TIMEOUT, sentry_capture=True)
        except RpcResourceNotFoundException:
            return cls._error_page(MSG_404, sentry_capture=True)
        except RpcBadRequestException as e:
            return cls._error_page(MSG_400,
                                   log="Got bad request, upstream returned status code {} with message {}."
                                   .format(*e.args),
                                   sentry_capture=True)
        except RpcClientException:
            return cls._error_page(MSG_400, sentry_capture=True)
        except RpcServerException:
            return cls._error_page(MSG_INTERNAL_ERROR, sentry_capture=True)
        except Exception:
            return cls._error_page(MSG_INTERNAL_ERROR, sentry_capture=True)

        return api_response

    @classmethod
    def call_with_handle_message(cls, url, params=None, retry=False, data=None) -> Union[Dict, Tuple]:
        """call API and handle exceptions.
        if exception, return a message
        """
        try:
            api_response = cls.call("GET", url, params=params, retry=retry, data=data)
        except RpcTimeoutException:
            return cls._return_string(408, "Backend timeout", sentry_capture=True)
        except RpcResourceNotFoundException:
            return cls._return_string(404, "Resource not found", sentry_capture=True)
        except RpcBadRequestException:
            return cls._return_string(400, "Bad request", sentry_capture=True)
        except RpcClientException:
            return cls._return_string(400, "Bad request", sentry_capture=True)
        except RpcServerException:
            return cls._return_string(500, "Server internal error", sentry_capture=True)
        except Exception:
            return cls._return_string(500, "Server internal error", sentry_capture=True)
        return api_response

import gevent
import requests
from flask import g, render_template

from everyclass.server import logger, sentry
from everyclass.server.exceptions import MSG_400, MSG_404, MSG_INTERNAL_ERROR, MSG_TIMEOUT, RpcBadRequestException, \
    RpcClientException, RpcResourceNotFoundException, RpcServerException, RpcTimeoutException
from everyclass.server.utils import plugin_available


class HttpRpc:
    @classmethod
    def _status_code_raise(cls, response: requests.Response):
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
    def _error_page(cls, message: str):
        """return a error page with a message. if sentry is available, tell user that they can report the problem."""
        sentry_param = {}
        if plugin_available("sentry"):
            sentry.captureException()
            sentry_param.update({"event_id"  : g.sentry_event_id,
                                 "public_dsn": sentry.client.get_public_dsn('https')
                                 })
        return render_template('common/error.html', message=message, **sentry_param)

    @classmethod
    def call(cls, url, params=None, retry=False, data=None):
        """call HTTP API. if server returns 4xx or 500 status code, raise exceptions.
        @:param params: parameters when calling RPC
        @:param retry: if set to True, will automatically retry
        """
        api_session = requests.sessions.session()
        trial_total = 5 if retry else 1
        trial = 0
        while trial < trial_total:
            try:
                with gevent.Timeout(5):
                    logger.debug('RPC GET {}'.format(url))
                    api_response = api_session.get(url, params=params, data=data)
            except gevent.timeout.Timeout:
                trial += 1
                continue
            cls._status_code_raise(api_response)
            logger.debug('RPC result: {}'.format(api_response.text))
            api_response = api_response.json()
            return api_response
        raise RpcTimeoutException('Timeout when calling {}. Tried {} time(s).'.format(url, trial_total))

    @classmethod
    def call_with_handle_flash(cls, url, params=None, retry=False, data=None):
        """call API and handle exceptions.
        if exception, flash a message and redirect to main page.
        """
        try:
            api_response = cls.call(url, params=params, retry=retry, data=data)
        except RpcTimeoutException:
            return cls._error_page(MSG_TIMEOUT)
        except RpcResourceNotFoundException:
            return cls._error_page(MSG_404)
        except RpcBadRequestException:
            return cls._error_page(MSG_400)
        except RpcClientException:
            return cls._error_page(MSG_400)
        except RpcServerException:
            return cls._error_page(MSG_INTERNAL_ERROR)
        except Exception:
            return cls._error_page(MSG_INTERNAL_ERROR)

        return api_response

    @classmethod
    def call_with_handle_message(cls, url, params=None, retry=False, data=None):
        """call API and handle exceptions.
        if exception, return a message
        """
        try:
            api_response = cls.call(url, params=params, retry=retry, data=data)
        except RpcTimeoutException as e:
            logger.warn(repr(e))
            return "Backend timeout", 408
        except RpcResourceNotFoundException as e:
            logger.info(repr(e))
            return "Resource not found", 404
        except RpcBadRequestException as e:
            logger.info(repr(e))
            return "Bad request", 400
        except RpcClientException as e:
            logger.error(repr(e))
            return "Bad request", 400
        except RpcServerException as e:
            logger.error(repr(e))
            return "Server internal error", 500
        except Exception as e:
            logger.error('RPC exception: {}'.format(repr(e)))
            return "Server internal error", 500
        return api_response

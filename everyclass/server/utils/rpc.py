import gevent
import requests
from flask import flash, redirect, url_for

from everyclass.server import logger
from everyclass.server.exceptions import RpcBadRequestException, RpcClientException, RpcResourceNotFoundException, \
    RpcServerException, RpcTimeoutException


class HttpRpc:
    @staticmethod
    def _status_code_raise(response: requests.Response):
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

    @staticmethod
    def _flash_and_redirect(message: str):
        """flash message and return to main page"""
        flash(message)
        return redirect(url_for('main.main'))

    @staticmethod
    def call(url, params=None, retry=False):
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
                    api_response = api_session.get(url, params=params)
            except gevent.timeout.Timeout:
                trial += 1
                continue
            HttpRpc._status_code_raise(api_response)
            logger.debug('RPC result: {}'.format(api_response.text))
            api_response = api_response.json()
            return api_response
        raise RpcTimeoutException('Timeout when calling {}. Tried {} time(s).'.format(url, trial_total))

    @staticmethod
    def call_with_handle_flash(url, params=None, retry=False):
        """call API and handle exceptions.
        if exception, flash a message and redirect to main page.
        """
        try:
            api_response = HttpRpc.call(url, params=params, retry=retry)
        except RpcTimeoutException as e:
            logger.warn(repr(e))
            return HttpRpc._flash_and_redirect('请求超时，请稍候再试')
        except RpcResourceNotFoundException as e:
            logger.info(repr(e))
            return HttpRpc._flash_and_redirect('资源不存在（404）')
        except RpcBadRequestException as e:
            logger.info(repr(e))
            return HttpRpc._flash_and_redirect('请求异常（400）')
        except RpcClientException as e:
            logger.error(repr(e))
            return HttpRpc._flash_and_redirect('请求错误')
        except RpcServerException as e:
            logger.error(repr(e))
            return HttpRpc._flash_and_redirect('服务器内部错误（500）。已经通知管理员，抱歉引起不便。')
        except Exception as e:
            logger.error('RPC exception: {}'.format(repr(e)))
            return HttpRpc._flash_and_redirect('服务器内部错误。已经通知管理员，抱歉引起不便。')
        return api_response

    @staticmethod
    def call_with_handle_message(url, params=None, retry=False):
        """call API and handle exceptions.
        if exception, return a message
        """
        try:
            api_response = HttpRpc.call(url, params=params, retry=retry)
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

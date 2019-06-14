from typing import Dict

import gevent
import requests

from everyclass.rpc import RpcBadRequest, RpcClientException, RpcResourceNotFound, RpcServerException, RpcTimeout, \
    _logger


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
                raise RpcResourceNotFound(status_code, response.text)
            if status_code == 400:
                raise RpcBadRequest(status_code, response.text)
            raise RpcClientException(status_code, response.text)

    @classmethod
    def call(cls, method: str, url: str, params=None, retry: bool = False, data=None, headers=None) -> Dict:
        """call HTTP API. if server returns 4xx or 500 status code, raise exceptions.

        :param method: HTTP method. Support GET or POST at the moment.
        :param url: URL of the HTTP endpoint
        :param params: parameters when calling RPC
        :param retry: if set to True, will automatically retry
        :param data: json data along with the request
        :param headers: custom headers
        """
        api_session = requests.sessions.session()
        trial_total = 5 if retry else 1
        trial = 0
        while trial < trial_total:
            try:
                _logger.debug('RPC {} {}'.format(method, url))
                if method == 'GET':
                    api_response = api_session.get(url, params=params, json=data, headers=headers)
                elif method == 'POST':
                    api_response = api_session.post(url, params=params, json=data, headers=headers)
                else:
                    raise NotImplementedError("Unsupported HTTP method {}".format(method))
            except gevent.timeout.Timeout:
                trial += 1
                continue
            cls._status_code_raise(api_response)
            response_json = api_response.json()
            _logger.debug('RPC result: {}'.format(response_json))
            return response_json
        raise RpcTimeout('Timeout when calling {}. Tried {} time(s).'.format(url, trial_total))

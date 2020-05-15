"""
HTTP API公共方法、错误码定义等
"""
import functools

from flask import request, g

from everyclass.server.utils.common_helpers import get_ut_uid, UTYPE_GUEST
from everyclass.server.utils.jsonable import to_json_response

# 请求错误
STATUS_CODE_INVALID_REQUEST = 4000
STATUS_CODE_TOKEN_MISSING = 4001
STATUS_CODE_INVALID_TOKEN = 4002
STATUS_CODE_PERMISSION_DENIED = 4003

# 服务器内部错误
STATUS_CODE_INTERNAL_ERROR = 5000

# 错误码对应的 status message
# 领域内业务错误的 status message 不用定义在这里
STATUS_MESSAGES = {
    STATUS_CODE_INVALID_REQUEST: 'invalid request',
    STATUS_CODE_TOKEN_MISSING: 'token is missing',
    STATUS_CODE_INVALID_TOKEN: 'token is invalid',
    STATUS_CODE_INTERNAL_ERROR: 'internal error',
}


def generate_success_response(obj):
    response_obj = {'status': 'success',
                    'data': obj}
    return to_json_response(response_obj)


def generate_error_response(obj, status_code: int, status_message_overwrite: str = None):
    response_obj = {'status': 'error',
                    'status_code': status_code,
                    'data': obj}
    if status_message_overwrite:
        response_obj.update({'status_message': status_message_overwrite})
    elif status_code in STATUS_MESSAGES:
        response_obj.update({'status_message': STATUS_MESSAGES[status_code]})
    else:
        response_obj.update({'status_message': "unknown error"})
    return to_json_response(response_obj)


def token_required(func):
    """
    检查是否携带token，如果token未携带或无效将直接返回错误，否则将username保存到g.username中
    """
    from everyclass.server.user import service as user_service

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        token = request.headers.get("X-API-Token")
        if not token:
            return generate_error_response(None, STATUS_CODE_TOKEN_MISSING)

        username = user_service.get_username_from_jwt(token)
        if not username:
            return generate_error_response(None, STATUS_CODE_INVALID_TOKEN)

        g.username = username
        return func(*args, **kwargs)

    return wrapped


def login_required(func):
    """检查用户是否已登录，如未登录则返回错误"""

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            ut, uid = get_ut_uid()
            if ut == UTYPE_GUEST:
                return generate_error_response(None, STATUS_CODE_PERMISSION_DENIED, "此功能需要登陆后使用")
        except NotImplementedError:
            return generate_error_response(None, STATUS_CODE_PERMISSION_DENIED, "检测身份时遇到未知错误")

        g.user_id = uid
        return func(*args, **kwargs)

    return wrapped

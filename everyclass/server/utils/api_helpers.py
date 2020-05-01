"""
HTTP API公共方法、错误码定义等
"""
from everyclass.server.utils.jsonable import to_json_response

STATUS_CODE_INVALID_REQUEST = 4000
STATUS_CODE_TOKEN_MISSING = 4001
STATUS_CODE_INTERNAL_ERROR = 5000

STATUS_MESSAGES = {
    STATUS_CODE_INTERNAL_ERROR: 'internal error',
    STATUS_CODE_TOKEN_MISSING: 'token is missing'
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

from everyclass.server.utils.jsonable import to_json_response

STATUS_CODE_INTERNAL_ERROR = 5000

STATUS_MESSAGES = {
    STATUS_CODE_INTERNAL_ERROR: 'internal error'
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

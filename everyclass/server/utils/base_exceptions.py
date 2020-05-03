"""
各领域中自定义错误类型的基类

有时候并不关注具体的错误，只需要知道错误的类型，这时候可以对这里定义的基类进行异常处理
"""
from everyclass.server.utils.api_helpers import STATUS_CODE_PERMISSION_DENIED, STATUS_CODE_INVALID_REQUEST, STATUS_CODE_INTERNAL_ERROR


class BizException(Exception):
    """所有业务错误类的基类，初始化时需要携带status_message和业务status_code"""

    def __init__(self, status_message: str, status_code: int):
        self.status_code = status_code
        self.status_message = status_message


class PermissionException(BizException):
    """权限相关错误"""

    def __init__(self, status_message, status_code: int = None):
        super().__init__(status_message, status_code if status_code else STATUS_CODE_PERMISSION_DENIED)


class InvalidRequestException(BizException):
    """请求无效"""

    def __init__(self, status_message, status_code: int = None):
        super().__init__(status_message, status_code if status_code else STATUS_CODE_INVALID_REQUEST)


class InternalError(BizException):
    """内部错误"""

    def __init__(self, status_message, status_code: int = None):
        super().__init__(status_message, status_code if status_code else STATUS_CODE_INTERNAL_ERROR)

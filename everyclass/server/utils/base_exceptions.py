"""
各领域中自定义错误类型的基类

有时候并不关注具体的错误，只需要知道错误的类型，这时候可以对这里定义的基类进行异常处理
"""


class PermissionException(BaseException):
    pass


class InvalidRequestException(BaseException):
    pass


class InternalError(BaseException):
    pass

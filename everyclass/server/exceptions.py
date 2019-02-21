class RpcException(ConnectionError):
    """HTTP 4xx or 5xx"""
    pass


class RpcTimeoutException(RpcException, TimeoutError):
    """timeout"""
    pass


class RpcClientException(RpcException):
    """HTTP 4xx"""
    pass


class RpcResourceNotFoundException(RpcClientException):
    """HTTP 404"""
    pass


class RpcBadRequestException(RpcClientException):
    """HTTP 400"""
    pass


class RpcServerException(RpcException):
    """HTTP 5xx"""
    pass


MSG_INTERNAL_ERROR = "抱歉。遇到了一个内部错误，请稍后重试或明天再来"
MSG_TIMEOUT = "请求超时，请稍后重试"
MSG_404 = "资源不存在"
MSG_400 = "你发起了一个异常的请求，请回到首页"
MSG_TOKEN_INVALID = "令牌无效或已过期，请重新开始注册流程"

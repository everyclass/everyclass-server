class RpcException(ConnectionError):
    """HTTP 4xx or 5xx"""
    pass


class RpcTimeout(RpcException, TimeoutError):
    """timeout"""
    pass


class RpcClientException(RpcException):
    """HTTP 4xx"""
    pass


class RpcResourceNotFound(RpcClientException):
    """HTTP 404"""
    pass


class RpcBadRequest(RpcClientException):
    """HTTP 400"""
    pass


class RpcServerException(RpcException):
    """HTTP 5xx"""
    pass


class RpcServerNotAvailable(RpcServerException):
    """HTTP 503"""
    pass

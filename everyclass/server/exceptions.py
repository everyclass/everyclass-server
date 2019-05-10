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


class RpcServerNotAvailable(RpcServerException):
    """HTTP 503"""
    pass

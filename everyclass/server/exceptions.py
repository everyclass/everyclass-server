class NoClassException(ValueError):
    pass


class NoStudentException(ValueError):
    pass


class IllegalSemesterException(ValueError):
    pass


class RpcException(ConnectionError):
    pass


class RpcClientException(RpcException):
    pass


class RpcServerException(RpcException):
    pass

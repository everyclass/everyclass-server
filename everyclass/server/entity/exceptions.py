from everyclass.server.utils import base_exceptions


class AlreadyReported(base_exceptions.InvalidRequestException):
    """报告教室占用时，重复报告"""

    def __init__(self):
        super().__init__("已经报告过了，请勿重复报告", 4100)

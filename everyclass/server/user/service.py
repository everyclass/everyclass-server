from typing import Optional, Tuple

from ddtrace import tracer
from flask import session
from zxcvbn import zxcvbn

from everyclass.rpc import RpcServerException
from everyclass.rpc.auth import Auth
from everyclass.server import logger
from everyclass.server.models import StudentSession
from everyclass.server.user.entity import IdentityVerifyRequest
from everyclass.server.user.repo import privacy_settings, user, simple_password, visit_count, user_id_sequence, identity_verify_requests


def get_privacy_level(student_id: str) -> int:
    return privacy_settings.get_level(student_id)


def set_privacy_level(student_id: str, new_level: int) -> None:
    return privacy_settings.set_level(student_id, new_level)


def add_user(sid_orig: str, password: str, password_encrypted: bool = False) -> None:
    return user.add_user(sid_orig, password, password_encrypted)


def user_exist(student_id: str) -> bool:
    return user.exist(student_id)


def check_password(sid_orig: str, password: str) -> bool:
    return user.check_password(sid_orig, password)


def record_simple_password(password: str, identifier: str) -> None:
    return simple_password.new(password, identifier)


def add_visitor_count(sid_orig: str, visitor: StudentSession = None) -> None:
    return visit_count.add_visitor_count(sid_orig, visitor)


def get_visitor_count(sid_orig: str) -> int:
    return visit_count.get_visitor_count(sid_orig)


def get_user_id() -> int:
    """user id 是APM系统中的用户标识，为递增数字，不是学号。如果session中保存了就使用session中的，否则新生成一个。"""
    if session.get('user_id', None):
        return session.get('user_id', None)
    return user_id_sequence.new()


def get_identity_verify_request_by_id(req_id: str) -> Optional[IdentityVerifyRequest]:
    """通过请求ID获取身份验证请求"""
    return identity_verify_requests.get_request_by_id(req_id)


class AlreadyRegisteredError(ValueError):
    """已经注册过了"""
    pass


def register_by_email(people_id: str) -> str:
    """向学生/老师的邮箱发送验证邮件"""
    if user_exist(people_id):
        raise AlreadyRegisteredError

    request_id = identity_verify_requests.new_register_request(people_id, "email", identity_verify_requests.ID_STATUS_SENT)

    with tracer.trace('send_email'):
        rpc_result = Auth.register_by_email(request_id, people_id)

    if rpc_result['acknowledged'] is False:
        raise RpcServerException("Unexpected acknowledge status")

    return request_id


class InvalidTokenError(ValueError):
    """邮件token无效"""
    pass


class IdentityVerifyRequestNotFoundError(ValueError):
    pass


def register_by_email_token_check(token: str) -> str:
    """检查邮件验证token有效性，并返回verification requestID"""
    with tracer.trace('verify_email_token'):
        rpc_result = Auth.verify_email_token(token=token)

    if not rpc_result.success:
        raise InvalidTokenError

    identity_verify_requests.set_request_status(rpc_result.request_id, identity_verify_requests.ID_STATUS_TKN_PASSED)

    req = identity_verify_requests.get_request_by_id(rpc_result.request_id)
    if not req:
        raise IdentityVerifyRequestNotFoundError

    student_id = req.identifier
    if user_exist(student_id):
        logger.info(f"User {student_id} try to register again by email token. Request filtered.")
        raise AlreadyRegisteredError

    return rpc_result.request_id


class IdentityVerifyRequestStatusError(ValueError):
    pass


class PasswordTooWeakError(ValueError):
    pass


def register_by_email_set_password(request_id: str, password: str) -> str:
    """通过邮件注册-设置密码，注册成功返回学号/教工号"""
    req = identity_verify_requests.get_request_by_id(request_id)
    if not req:
        raise IdentityVerifyRequestNotFoundError

    if req.status != identity_verify_requests.ID_STATUS_TKN_PASSED:
        raise IdentityVerifyRequestStatusError

    # 密码强度检查
    if score_password_strength(password) < 2:
        record_simple_password(password=password, identifier=req.identifier)
        raise PasswordTooWeakError

    try:
        add_user(req.identifier, password, False)
    except ValueError as e:
        logger.info(f"User {req.identifier} try to register again by email token. The request is rejected by database.")
        raise AlreadyRegisteredError from e

    identity_verify_requests.set_request_status(str(req.request_id), identity_verify_requests.ID_STATUS_PASSWORD_SET)
    return req.identifier


def register_by_password(jw_password: str, password: str, identifier: str) -> str:
    """通过教务密码注册，返回request id"""
    # 密码强度检查
    if score_password_strength(password) < 2:
        record_simple_password(password=password, identifier=identifier)
        raise PasswordTooWeakError

    request_id = identity_verify_requests.new_register_request(identifier,
                                                               "password",
                                                               identity_verify_requests.ID_STATUS_WAIT_VERIFY,
                                                               password=password)
    # call everyclass-auth to verify password
    with tracer.trace('register_by_password'):
        rpc_result = Auth.register_by_password(request_id=str(request_id),
                                               student_id=identifier,
                                               password=jw_password)

    if not rpc_result['acknowledged']:
        raise RpcServerException("acknowledge status not expected")

    return request_id


class IdentityVerifyMethodNotExpectedError(ValueError):
    pass


class RequestIDUsed(ValueError):
    pass


def register_by_password_status_refresh(request_id: str) -> Tuple[bool, str, Optional[str]]:
    """通过教务密码注册-刷新状态，返回是否成功、auth message及学号/教工号（如果成功）"""
    req = identity_verify_requests.get_request_by_id(request_id)
    if not req:
        raise IdentityVerifyRequestNotFoundError
    if req.method != "password":
        logger.warn("Non-password verification request is trying get status from password interface")
        raise IdentityVerifyMethodNotExpectedError
    if req.method == identity_verify_requests.ID_STATUS_PWD_SUCCESS:
        raise RequestIDUsed("Request ID is used and password is set. It cannot be reused.")

    # fetch status from everyclass-auth
    with tracer.trace('get_result'):
        rpc_result = Auth.get_result(str(request_id))

    if rpc_result.success:  # 密码验证通过，设置请求状态并新增用户
        identity_verify_requests.set_request_status(str(request_id), identity_verify_requests.ID_STATUS_PWD_SUCCESS)

        verification_req = identity_verify_requests.get_request_by_id(str(request_id))

        try:
            add_user(sid_orig=verification_req.identifier, password=verification_req.extra["password"],
                     password_encrypted=True)
        except ValueError as e:
            raise AlreadyRegisteredError from e

        return True, "SUCCESS", verification_req.identifier
    else:
        # 如果不是成功状态则返回auth服务返回的message
        return False, rpc_result.message, None


def score_password_strength(password: str) -> int:
    return zxcvbn(password=password)['score']

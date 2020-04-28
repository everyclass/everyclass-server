import uuid
from typing import Optional, Tuple, List

from ddtrace import tracer
from flask import session
from zxcvbn import zxcvbn

from everyclass.rpc import RpcServerException
from everyclass.rpc.auth import Auth
from everyclass.server import logger
from everyclass.server.entity import service as entity_service
from everyclass.server.user.model import User, VerificationRequest, SimplePassword, Visitor
from everyclass.server.user.repo import privacy_settings, visit_count, user_id_sequence, visit_track
from everyclass.server.utils.session import USER_TYPE_TEACHER, USER_TYPE_STUDENT

"""Registration and Login"""


class UserNotExists(BaseException):
    pass


def add_user(identifier: str, password: str, password_encrypted: bool = False) -> None:
    return User.add_user(identifier, password, password_encrypted)


def user_exist(identifier: str) -> bool:
    return User.exists(identifier)


def check_password(identifier: str, password: str) -> bool:
    user = User.get_by_id(identifier)
    if not user:
        raise UserNotExists
    return User.get_by_id(identifier).check_password(password)


def record_simple_password(password: str, identifier: str) -> None:
    return SimplePassword.new(password, identifier)


class AlreadyRegisteredError(ValueError):
    """已经注册过了"""
    pass


def register_by_email(identifier: str) -> str:
    """向学生/老师的邮箱发送验证邮件"""
    if user_exist(identifier):
        raise AlreadyRegisteredError

    request_id = VerificationRequest.new_email_request(identifier)

    with tracer.trace('send_email'):
        rpc_result = Auth.register_by_email(request_id, identifier)

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

    request = VerificationRequest.find_by_id(uuid.UUID(rpc_result.request_id))
    if not request:
        raise IdentityVerifyRequestNotFoundError
    request.set_status_token_passed()

    student_id = request.identifier
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
    req = VerificationRequest.find_by_id(uuid.UUID(request_id))
    if not req:
        raise IdentityVerifyRequestNotFoundError

    if req.status != VerificationRequest.STATUS_TKN_PASSED:
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

    VerificationRequest.find_by_id(req.request_id).set_status_password_set()
    return req.identifier


def register_by_password(jw_password: str, password: str, identifier: str) -> str:
    """通过教务密码注册，返回request id"""
    # 密码强度检查
    if score_password_strength(password) < 2:
        record_simple_password(password=password, identifier=identifier)
        raise PasswordTooWeakError
    request_id = VerificationRequest.new_password_request(identifier, password)
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
    req = VerificationRequest.find_by_id(uuid.UUID(request_id))
    if not req:
        raise IdentityVerifyRequestNotFoundError
    if req.method != "password":
        logger.warn("Non-password verification request is trying get status from password interface")
        raise IdentityVerifyMethodNotExpectedError
    if req.method == VerificationRequest.STATUS_PWD_SUCCESS:
        raise RequestIDUsed("Request ID is used and password is set. It cannot be reused.")

    # fetch status from everyclass-auth
    with tracer.trace('get_result'):
        rpc_result = Auth.get_result(str(request_id))

    if rpc_result.success:  # 密码验证通过，设置请求状态并新增用户
        verification_req = VerificationRequest.find_by_id(uuid.UUID(request_id))
        verification_req.set_status_success()

        try:
            add_user(identifier=verification_req.identifier, password=verification_req.extra["password"],
                     password_encrypted=True)
        except ValueError as e:
            raise AlreadyRegisteredError from e

        return True, "SUCCESS", verification_req.identifier
    else:
        # 如果不是成功状态则返回auth服务返回的message
        return False, rpc_result.message, None


def score_password_strength(password: str) -> int:
    return zxcvbn(password=password)['score']


"""Privacy"""


def get_privacy_level(student_id: str) -> int:
    return privacy_settings.get_level(student_id)


def set_privacy_level(student_id: str, new_level: int) -> None:
    return privacy_settings.set_level(student_id, new_level)


"""Visiting"""


class LoginRequired(Exception):
    pass


class PermissionAdjustRequired(Exception):
    pass


def has_access(host: str, visitor: Optional[str] = None, footprint: bool = True) -> bool:
    """检查访问者是否有权限访问学生课表。footprint为True将会留下访问记录并增加访客计数。
    """
    privacy_level = get_privacy_level(host)
    # 仅自己可见、且未登录或登录用户非在查看的用户，拒绝访问
    if privacy_level == 2 and (not visitor or visitor != host):
        return False

    # 实名互访
    if privacy_level == 1:
        # 未登录，要求登录
        if not visitor:
            raise LoginRequired
        # 仅自己可见的用户访问实名互访的用户，拒绝，要求调整自己的权限
        if get_privacy_level(visitor) == 2:
            raise PermissionAdjustRequired

    # 公开或实名互访模式、已登录、不是自己访问自己，则留下轨迹
    if footprint and privacy_level != 2 and visitor and visitor != host:
        _update_track(host=host, visitor=visitor)
        _add_visitor_count(host=host, visitor=visitor)
    return True


def _update_track(host: str, visitor: str) -> None:
    return visit_track.update_track(host, visitor)


def _add_visitor_count(host: str, visitor: str = None) -> None:
    return visit_count.add_visitor_count(host, visitor)


def get_visitor_count(identifier: str) -> int:
    return visit_count.get_visitor_count(identifier)


def get_visitors(identifier: str) -> List[Visitor]:
    result = visit_track.get_visitors(identifier)

    visitor_list = []
    for record in result:
        # query entity to get rich results
        # todo: entity add a multi GET interface to make this process faster when the list is long
        search_result = entity_service.search(record[0])
        if len(search_result.students) > 0:
            visitor_list.append(Visitor(name=search_result.students[0].name,
                                        user_type=USER_TYPE_STUDENT,
                                        identifier_encoded=search_result.students[0].student_id_encoded,
                                        last_semester=search_result.students[0].semesters[-1],
                                        visit_time=record[1]))
        elif len(search_result.teachers) > 0:
            visitor_list.append(Visitor(name=search_result.teachers[0].name,
                                        user_type=USER_TYPE_TEACHER,
                                        identifier_encoded=search_result.teachers[0].teacher_id_encoded,
                                        last_semester=search_result.teachers[0].semesters[-1],
                                        visit_time=record[1]))
    return visitor_list


"""User sequence num"""


def get_user_id() -> int:
    """user id 是APM系统中的用户标识，为递增数字，不是学号。如果session中保存了就使用session中的，否则新生成一个。"""
    if session.get('user_id', None):
        return session.get('user_id', None)
    return user_id_sequence.new()

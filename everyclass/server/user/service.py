import uuid
from typing import Optional, Tuple, List, Dict

import jwt
from ddtrace import tracer
from flask import session
from zxcvbn import zxcvbn

from everyclass.rpc import RpcServerException
from everyclass.rpc.auth import Auth
from everyclass.server import logger
from everyclass.server.entity import service as entity_service
from everyclass.server.user.exceptions import RecordNotFound, NoPermissionToAccept, UserNotExists, \
    AlreadyRegisteredError, InvalidTokenError, IdentityVerifyRequestNotFoundError, PasswordTooWeakError, IdentityVerifyRequestStatusError
from everyclass.server.user.model import User, VerificationRequest, SimplePassword, Visitor, Grant
from everyclass.server.user.repo import privacy_settings, visit_count, user_id_sequence, visit_track
from everyclass.server.utils.base_exceptions import InternalError
from everyclass.server.utils.session import USER_TYPE_TEACHER, USER_TYPE_STUDENT

"""Registration and Login"""


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


def register_by_email(identifier: str) -> str:
    """向学生/老师的邮箱发送验证邮件"""
    if user_exist(identifier):
        raise AlreadyRegisteredError

    request_id = VerificationRequest.new_email_request(identifier)

    with tracer.trace('send_email'):
        rpc_result = Auth.register_by_email(request_id, identifier)

    if rpc_result['acknowledged'] is False:
        raise InternalError("Unexpected acknowledge status")

    return request_id


def register_by_email_token_check(token: str) -> str:
    """检查邮件验证token有效性，并返回verification requestID"""
    with tracer.trace('verify_email_token'):
        rpc_result = Auth.verify_email_token(token=token)

    if not rpc_result.success:
        raise InvalidTokenError

    request = VerificationRequest.find_by_id(uuid.UUID(rpc_result.request_id))
    if not request:
        logger.error(f"can not find related verification request of email token {token}")
    if request.status != VerificationRequest.STATUS_TKN_PASSED:
        request.set_status_token_passed()

    student_id = request.identifier
    if user_exist(student_id):
        logger.info(f"User {student_id} try to register again by email token. Request filtered.")
        raise AlreadyRegisteredError

    return rpc_result.request_id


def register_by_email_set_password(request_id: str, password: str) -> str:
    """通过邮件注册-设置密码，注册成功返回学号/教工号"""
    req = VerificationRequest.find_by_id(uuid.UUID(request_id))
    if not req:
        raise IdentityVerifyRequestNotFoundError

    if req.status == VerificationRequest.STATUS_PASSWORD_SET:
        # 已经注册，重复请求，当做成功
        return req.identifier

    if req.status != VerificationRequest.STATUS_TKN_PASSED:
        raise IdentityVerifyRequestStatusError

    # 密码强度检查
    if score_password_strength(password) < 2:
        record_simple_password(password=password, identifier=req.identifier)
        raise PasswordTooWeakError

    add_user(req.identifier, password, False)

    req.set_status_password_set()
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

        add_user(identifier=verification_req.identifier, password=verification_req.extra["password"], password_encrypted=True)

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

REASON_LOGIN_REQUIRED = 'require_login'
REASON_PERMISSION_ADJUST_REQUIRED = 'require_permission_adjust'
REASON_SELF_ONLY = 'self_only'


def has_access(host: str, visitor: Optional[str] = None, footprint: bool = True) -> (bool, Optional[str]):
    """检查访问者是否有权限访问学生课表。footprint为True将会留下访问记录并增加访客计数。
    """
    if visitor and Grant.has_grant(visitor, host):
        return True, None

    privacy_level = get_privacy_level(host)
    # 仅自己可见、且未登录或登录用户非在查看的用户，拒绝访问
    if privacy_level == 2 and (not visitor or visitor != host):
        return False, REASON_SELF_ONLY

    # 实名互访
    if privacy_level == 1:
        # 未登录，要求登录
        if not visitor:
            return False, REASON_LOGIN_REQUIRED
        # 仅自己可见的用户访问实名互访的用户，拒绝，要求调整自己的权限
        if get_privacy_level(visitor) == 2:
            return False, REASON_PERMISSION_ADJUST_REQUIRED

    # 公开或实名互访模式、已登录、不是自己访问自己，则留下轨迹
    if footprint and privacy_level != 2 and visitor and visitor != host:
        _update_track(host=host, visitor=visitor)
        _add_visitor_count(host=host, visitor=visitor)
    return True, None


"""granting"""


def new_grant_request(from_uid: str, to_uid: str):
    return Grant.request_for_grant(from_uid, to_uid)


def get_pending_requests(user_identifier: str):
    return Grant.get_requests(user_identifier)


def accept_grant(grant_id: int, current_user_id: str):
    grant = Grant.get_by_id(grant_id)
    if not grant:
        raise RecordNotFound("grant id not found")

    if grant.to_user_id != current_user_id:
        raise NoPermissionToAccept(f"the record {grant_id} does not belong to user {current_user_id}")

    grant.accept()


def reject_grant(grant_id: int, current_user_id: str):
    grant = Grant.get_by_id(grant_id)
    if not grant:
        raise RecordNotFound("grant id not found")

    if grant.to_user_id != current_user_id:
        raise NoPermissionToAccept(f"the record {grant_id} does not belong to user {current_user_id}")

    grant.reject()


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


"""JWT Token"""


def issue_token(user_identifier: str) -> str:
    """签发指定用户名的JWT token"""
    from everyclass.server.utils.config import get_config
    config = get_config()

    payload = {"username": user_identifier}
    token = jwt.encode(payload, config.JWT_PRIVATE_KEY, algorithm='RS256')

    return token.decode('utf8')


def decode_jwt_payload(token: str) -> Dict:
    """验证JWT Token并解出payload

    如果payload被修改，抛出jwt.exceptions.InvalidSignatureError。如果签名被修改，抛出jwt.exceptions.DecodeError
    """
    from everyclass.server.utils.config import get_config
    config = get_config()

    return jwt.decode(token, config.JWT_PUBLIC_KEY, algorithms=['RS256'])


def get_username_from_jwt(token: str) -> Optional[str]:
    """从JWT token中解析出用户名，如果解析失败，返回None"""
    from everyclass.server import logger

    if not token:
        logger.warn(f"empty token received, type: {type(token)}")

    try:
        payload = decode_jwt_payload(token)
    except jwt.exceptions.PyJWTError as e:
        logger.warn("JWT token decode failed, maybe it was tampered with client side", extra={"token": token,
                                                                                              "error": repr(e)})
        return None

    if 'username' not in payload:
        logger.warn("aud not in payload. the token is weird.")
        return None
    return payload["username"]

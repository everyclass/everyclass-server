from flask import Blueprint, g, request, session

from everyclass.server.user import exceptions
from everyclass.server.user import service as user_service
from everyclass.server.utils import generate_success_response, generate_error_response, api_helpers
from everyclass.server.utils.api_helpers import token_required
from everyclass.server.utils.common_helpers import get_ut_uid, UTYPE_GUEST
from everyclass.server.utils.encryption import decrypt, RTYPE_STUDENT
from everyclass.server.utils.web_consts import SESSION_EMAIL_VER_REQ_ID

user_api_bp = Blueprint('api_user', __name__)


@user_api_bp.route('/_login', methods=["POST"])
def login():
    """登录并获得token

    可能的错误码：
    4000 用户名或密码错误
    4100 用户不存在
    4101 密码错误
    """
    username = request.form.get("username")
    password = request.form.get("password")
    if not username:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, "请填写用户名")
    if not password:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, "请填写密码")

    if not user_service.check_password(username, password):
        raise exceptions.WrongPassword
    return generate_success_response({"token": user_service.issue_token(username)})


@user_api_bp.route('/_register_by_email')
def register_by_email():
    """通过邮箱验证注册

    错误码：
    4000 用户名未填写
    4102 已经注册过了
    5000 内部错误

    todo：加限流
    """
    identifier = request.args.get("identifier")
    if not identifier:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, "请填写用户名")
    user_service.register_by_email(identifier)
    return generate_success_response(None)


@user_api_bp.route('/_email_verification_check')
def email_verification_check():
    """验证邮箱token

    错误码：
    4000 token缺失
    4102 用户已存在，token无效
    4103 token无效
    """
    # todo 这里发出去的邮箱里面的链接还是网页版的，要换一下

    email_token = request.args.get("token")
    if not email_token:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, "token参数缺失")
    request_id = user_service.register_by_email_token_check(email_token)
    session[SESSION_EMAIL_VER_REQ_ID] = request_id
    return generate_success_response(None)


@user_api_bp.route('/_email_verification_set_password', methods=['POST'])
def email_verification():
    """邮件验证-设置密码

    错误码：
    4104 验证请求不存在（内部异常）
    4105 当前VerificationRequest的状态并非STATUS_TKN_PASSED（排除网络卡了导致客户端没收到响应其实已经注册成功的情况）
    4106 密码过弱
    """
    request_id = session.get(SESSION_EMAIL_VER_REQ_ID, None)
    if not request_id:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, "无效请求，请重新点击邮件中的链接")

    password = request.form.get("password")
    if not password:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, "请输入密码")

    username = user_service.register_by_email_set_password(request_id, password)
    return generate_success_response({"token": user_service.issue_token(username)})


@user_api_bp.route('/grants/_apply')
def apply_grant():
    to_user_id_encoded = request.args.get('to_user_id')
    if not to_user_id_encoded:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, "mising to_user_id")

    ut, uid = get_ut_uid()
    if ut == UTYPE_GUEST:
        return generate_error_response(None, api_helpers.STATUS_CODE_PERMISSION_DENIED, "您需要登录才能进行此操作")

    to_uid = decrypt(to_user_id_encoded, resource_type=RTYPE_STUDENT)[1]

    user_service.new_grant_request(uid, to_uid)
    return generate_success_response(None)


@user_api_bp.route('/grants/_my_pending')
@token_required
def my_pending_grants():
    return generate_success_response(user_service.get_pending_requests(g.username))


@user_api_bp.route('/grants/<int:grant_id>/_accept')
@token_required
def accept_grant(grant_id: int):
    return generate_success_response(user_service.accept_grant(grant_id, g.username))

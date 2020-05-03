from flask import Blueprint, g, request

from everyclass.server.user import exceptions
from everyclass.server.user import service as user_service
from everyclass.server.utils import generate_success_response, generate_error_response, api_helpers
from everyclass.server.utils.api_helpers import token_required

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
        raise exceptions.WrongPassword("密码错误")
    return generate_success_response({"token": user_service.issue_token(username)})


@user_api_bp.route('/grants/_my_pending')
@token_required
def my_pending_grants():
    return generate_success_response(user_service.get_pending_requests(g.username))


@user_api_bp.route('/grants/<int:grant_id>/_accept')
@token_required
def accept_grant(grant_id: int):
    return generate_success_response(user_service.accept_grant(grant_id, g.username))

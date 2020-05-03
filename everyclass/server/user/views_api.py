from flask import Blueprint, g

from everyclass.server.user import service as user_service
from everyclass.server.utils import generate_success_response
from everyclass.server.utils.api_helpers import token_required

user_api_bp = Blueprint('api_user', __name__)


@user_api_bp.route('/grants/_my_pending')
@token_required
def my_pending_grants():
    return generate_success_response(user_service.get_pending_requests(g.username))


@user_api_bp.route('/grants/<int:grant_id>/_accept')
@token_required
def accept_grant(grant_id: int):
    return generate_success_response(user_service.accept_grant(grant_id, g.username))

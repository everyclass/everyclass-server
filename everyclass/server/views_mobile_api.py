import datetime

from flask import Blueprint, request

from everyclass.server.entity import service as entity_service
from everyclass.server.user import service as user_service
from everyclass.server.utils import generate_error_response, api_helpers, generate_success_response

mobile_blueprint = Blueprint('mobile_api', __name__)


@mobile_blueprint.route('/multi_people_schedule')
def multi_people_schedule():
    token = request.headers["X-API-Token"]
    if not token:
        return generate_error_response(None, api_helpers.STATUS_CODE_TOKEN_MISSING)

    username = user_service.get_username_from_jwt(token)

    people = request.args['people']
    date = request.args['date']

    if not people:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing people parameter')
    if not date:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing date parameter')

    people_list = people.split(',')
    date = datetime.date(*map(int, date.split('-')))
    schedule = entity_service.multi_people_schedule(people_list, date, username)
    return generate_success_response(schedule)

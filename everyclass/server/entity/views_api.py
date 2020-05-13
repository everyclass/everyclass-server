import datetime

from flask import Blueprint, request, g

from everyclass.server.entity import service as entity_service
from everyclass.server.utils import generate_error_response, api_helpers, generate_success_response
from everyclass.server.utils.api_helpers import token_required

entity_api_bp = Blueprint('api_entity', __name__)


@entity_api_bp.route('/multi_people_schedule')
@token_required
def multi_people_schedule():
    people = request.args['people']
    date = request.args['date']

    if not people:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing people parameter')
    if not date:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing date parameter')

    people_list = people.split(',')
    date = datetime.date(*map(int, date.split('-')))
    schedule = entity_service.multi_people_schedule(people_list, date, g.username)
    return generate_success_response(schedule)


@entity_api_bp.route('/room')
def get_all_rooms():
    return generate_success_response(entity_service.get_rooms())


@entity_api_bp.route('/room/_available')
def get_available_rooms():
    campus = request.args['campus']
    building = request.args['building']
    time = request.args['time']
    date_str = request.args['date']
    date = datetime.date(*map(int, date_str.split('-')))

    if not campus:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing campus parameter')
    if not building:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing building parameter')
    if not time:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing time parameter')
    if not date_str:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing date parameter')

    return generate_success_response(entity_service.get_available_rooms(campus, building, date, time))

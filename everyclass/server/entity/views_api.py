import datetime

from flask import Blueprint, request, g

from everyclass.server.entity import service as entity_service
from everyclass.server.utils import generate_error_response, api_helpers, generate_success_response
from everyclass.server.utils.api_helpers import token_required
from everyclass.server.utils.common_helpers import get_user_id
from everyclass.server.utils.encryption import decrypt, RTYPE_ROOM

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
    campus = request.args.get('campus')
    building = request.args.get('building')
    time = request.args.get('time')
    date_str = request.args.get('date')
    if not date_str:
        date = datetime.date.today()
    else:
        date = datetime.date(*map(int, date_str.split('-')))

    # vip 可以选择日期，普通用户只能选择时间

    if not campus:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing campus parameter')
    if not building:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing building parameter')
    if not time:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing time parameter')

    return generate_success_response(entity_service.get_available_rooms(campus, building, date, time))


@entity_api_bp.route('/room/_report_unavailable')
def report_unavailable_room():
    room_id_encoded = request.args.get("room_id")
    time = request.args.get("time")
    date_str = request.args.get("date")
    date = datetime.date(*map(int, date_str.split('-')))

    # 运营策略：报告获得他人认同可以加积分

    if not room_id_encoded:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing room_id parameter')
    if not time:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing time parameter')
    if not date_str:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing date parameter')

    try:
        resource_type, room_id = decrypt(room_id_encoded, resource_type=RTYPE_ROOM)
    except ValueError:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'invalid room_id')

    entity_service.report_unavailable_room(room_id, date, time, *get_user_id())
    return generate_success_response(None)

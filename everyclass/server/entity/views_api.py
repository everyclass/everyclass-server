import datetime
import re

from flask import Blueprint, request

from everyclass.server.entity import service as entity_service
from everyclass.server.entity.model import SearchResultItem
from everyclass.server.user import service as user_service
from everyclass.server.utils import generate_error_response, api_helpers, generate_success_response
from everyclass.server.utils.common_helpers import get_logged_in_uid, get_ut_uid
from everyclass.server.utils.encryption import decrypt, RTYPE_ROOM

entity_api_bp = Blueprint('api_entity', __name__)


@entity_api_bp.route('/multi_people_schedule')
def multi_people_schedule():
    people_encoded = request.args.get('people')
    date = request.args.get('date')

    uid = get_logged_in_uid()

    if not people_encoded:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing people parameter')
    if not date:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing date parameter')

    people_list = [decrypt(people)[1] for people in people_encoded.split(',')]
    date = datetime.date(*map(int, date.split('-')))
    schedule = entity_service.multi_people_schedule(people_list, date, uid)
    return generate_success_response(schedule)


@entity_api_bp.route('/multi_people_schedule/_search')
def multi_people_schedule_search():
    keyword = request.args.get('keyword')
    if not keyword:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, 'missing keyword parameter')

    print([request.cookies.get('e_session')])

    search_result = entity_service.search(keyword)

    uid = get_logged_in_uid()

    print(uid)

    items = []
    for s in search_result.students:
        eligible = False
        groups = re.findall(r'\d+', s.klass)
        if len(groups) > 0:
            if int(groups[0][:2]) + 5 >= datetime.date.today().year - 2000:
                eligible = True
        else:
            eligible = True

        if eligible:
            items.append(SearchResultItem(s.name, s.deputy + s.klass, "student", s.student_id_encoded,
                                          *user_service.has_access(s.student_id, uid, False)))

    items.extend([SearchResultItem(t.name, t.unit + t.title, "teacher", t.teacher_id_encoded,
                                   *user_service.has_access(t.teacher_id, uid, False)) for t in search_result.teachers])
    return generate_success_response({'items': items, 'keyword': keyword, 'is_guest': True if uid is None else False})


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

    entity_service.report_unavailable_room(room_id, date, time, *get_ut_uid())
    return generate_success_response(None)

import datetime

from flask import Blueprint, request

from everyclass.server.entity import service as entity_service
from everyclass.server.utils import generate_error_response, api_common, generate_success_response

mobile_blueprint = Blueprint('mobile_api', __name__)


@mobile_blueprint.route('/multi_people_schedule')
def multi_people_schedule():
    people = request.args['people']
    date = request.args['date']

    if not people:
        return generate_error_response(None, api_common.STATUS_CODE_INVALID_REQUEST, 'missing people parameter')
    if not date:
        return generate_error_response(None, api_common.STATUS_CODE_INVALID_REQUEST, 'missing date parameter')

    people_list = people.split(',')
    date = datetime.date(*map(int, date.split('-')))
    schedule = entity_service.multi_people_schedule(people_list, date)
    return generate_success_response(schedule)


@mobile_blueprint.app_errorhandler(500)
def internal_exception(error):
    return generate_error_response(None, api_common.STATUS_CODE_INTERNAL_ERROR)

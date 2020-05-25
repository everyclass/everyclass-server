from flask import Blueprint, request

from everyclass.server.course import service as course_service
from everyclass.server.course.model import Answer, AnswerSheet
from everyclass.server.utils import generate_success_response

course_api_bp = Blueprint('api_course', __name__)


@course_api_bp.route('/_categories')
def class_categories():
    return generate_success_response(course_service.get_class_categories())


@course_api_bp.route('/_questionnaire')
def get_advice_questionnaire():
    return generate_success_response(course_service.get_advice_questions())


@course_api_bp.route('/_advice')
def get_advice():
    args = request.args
    answers = []
    for k, v in args.items():
        answers.append(Answer(int(k), list(map(int, v.split(',')))))
    return generate_success_response(course_service.get_advice_result(AnswerSheet(answers)))

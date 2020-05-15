from flask import Blueprint, g, url_for

from everyclass.server.calendar import service as calendar_service
from everyclass.server.entity import service as entity_service
from everyclass.server.user import service as user_service
from everyclass.server.utils import generate_success_response, generate_error_response, api_helpers, encryption
from everyclass.server.utils.api_helpers import token_required

calendar_api_bp = Blueprint('api_calendar', __name__)


@calendar_api_bp.route('/<string:id_sec>/semester/<string:semester>/_token')
@token_required
def get_calendar_token(id_sec: str, semester: str):
    """

    :param id_sec: 加密后的学号或教工号
    :param semester: 学期，如 2018-2019-1

    错误码：
    4000 请求无效
    4003 无权访问
    """
    try:
        res_type, res_id = encryption.decrypt(id_sec)
    except ValueError:
        return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, '用户ID无效')

    if res_type == encryption.RTYPE_STUDENT:
        if not user_service.has_access(res_id, g.username)[0]:
            return generate_error_response(None, api_helpers.STATUS_CODE_PERMISSION_DENIED, '无权访问该用户课表')
        student = entity_service.get_student_timetable(res_id, semester)
        if not student:
            return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, '学生不存在')
        token = calendar_service.get_calendar_token(resource_type=res_type,
                                                    identifier=student.student_id,
                                                    semester=semester)
    else:
        teacher = entity_service.get_teacher_timetable(res_id, semester)
        if not teacher:
            return generate_error_response(None, api_helpers.STATUS_CODE_INVALID_REQUEST, '教师不存在')
        token = calendar_service.get_calendar_token(resource_type=res_type,
                                                    identifier=teacher.teacher_id,
                                                    semester=semester)

    ics_url = url_for('calendar.ics_download', calendar_token=token, _external=True)
    ics_webcal = ics_url.replace('https', 'webcal').replace('http', 'webcal')
    return generate_success_response({'token': token,
                                      'ics_url': ics_url,
                                      'ics_url_webcal': ics_webcal})

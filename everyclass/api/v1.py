from flask import jsonify

from . import api_v1


@api_v1.route('/students/<student_id>/semesters')
def get_semesters(student_id):
    """
    提供学号，返回一个学生可用的学期。

    :param student_id: 学号
    """
    from db_operations import get_my_semesters
    semesters, student_name = get_my_semesters(student_id)
    response = jsonify({'name': student_name, 'semesters': semesters})
    return response


@api_v1.route('/students/<student_id>/semesters/<semester>/courses')
def get_courses(student_id, semester):
    """
    提供学号与学期，返回学生当前学期的课表。

    :param student_id: 学号
    :param semester: 学期
    """
    from db_operations import get_classes_for_student
    try:
        courses = get_classes_for_student(student_id, semester)
        print(courses)
        courses_to_return = {}
        for k, v in courses.items():
            if str(k[0]) not in courses_to_return:
                courses_to_return[str(k[0])] = {}
            courses_to_return[str(k[0])][str(k[1])] = v
        import json

        return json.dumps({'courses': courses_to_return})
    except FileExistsError:
        response = jsonify({'error': 'exception'})
        response.status_code = 400
        return response


@api_v1.errorhandler(403)
def error_handler_403():
    """handle resource not found error"""
    response = jsonify({'error': 'forbidden'})
    response.status_code = 403
    return response


@api_v1.errorhandler(500)
def error_handler_500():
    """handle 500 error"""
    response = jsonify({'error': 'server internal error'})
    response.status_code = 500
    return response

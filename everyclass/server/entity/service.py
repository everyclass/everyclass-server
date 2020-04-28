from typing import Tuple, Union

from everyclass.rpc.entity import SearchResultStudentItem, SearchResultTeacherItem, Entity, SearchResult, CardResult


def search(keyword: str) -> SearchResult:
    return Entity.search(keyword)


def get_student(student_id: str):
    return Entity.get_student(student_id)


def get_student_timetable(student_id: str, semester: str):
    return Entity.get_student_timetable(student_id, semester)


def get_teacher_timetable(teacher_id: str, semester: str):
    return Entity.get_teacher_timetable(teacher_id, semester)


def get_classroom_timetable(semester: str, room_id: str):
    return Entity.get_classroom_timetable(semester, room_id)


def get_card(semester: str, card_id: str) -> CardResult:
    return Entity.get_card(semester, card_id)


def get_teacher(teacher_id: str):
    return Entity.get_teacher(teacher_id)


class PeopleNotFoundError(ValueError):
    pass


def get_people_info(identifier: str) -> Tuple[bool, Union[SearchResultStudentItem, SearchResultTeacherItem]]:
    """
    获得一个人（学生或老师）的基本信息

    :param identifier: student ID or teacher ID
    :return: The first parameter is a Union[bool, None]. True means it's a student, False means it's a teacher. If
     the identifier is not found, a PeopleNotFoundError is raised. The second parameter is the info of student or
     teacher.
    """
    result = search(identifier)
    if len(result.students) > 0:
        return True, result.students[0]
    if len(result.teachers) > 0:
        return False, result.teachers[0]
    raise PeopleNotFoundError

import datetime
from typing import Tuple, Union, List

from everyclass.rpc.entity import SearchResultStudentItem, SearchResultTeacherItem, Entity, SearchResult, CardResult
from everyclass.server.entity.domain import replace_exception
from everyclass.server.entity.model import MultiPeopleSchedule, AllRooms, AvailableRooms, UnavailableRoomReport


@replace_exception
def search(keyword: str) -> SearchResult:
    return Entity.search(keyword)


@replace_exception
def get_student(student_id: str):
    return Entity.get_student(student_id)


@replace_exception
def get_student_timetable(student_id: str, semester: str):
    return Entity.get_student_timetable(student_id, semester)


@replace_exception
def get_teacher_timetable(teacher_id: str, semester: str):
    return Entity.get_teacher_timetable(teacher_id, semester)


@replace_exception
def get_classroom_timetable(semester: str, room_id: str):
    return Entity.get_classroom_timetable(semester, room_id)


@replace_exception
def get_card(semester: str, card_id: str) -> CardResult:
    return Entity.get_card(semester, card_id)


@replace_exception
def get_teacher(teacher_id: str):
    return Entity.get_teacher(teacher_id)


@replace_exception
def get_rooms():
    return AllRooms.make(Entity.get_rooms())


@replace_exception
def get_available_rooms(campus: str, building: str, date: datetime.date, time: str):
    # time 格式为0102这种，表示第1-2节
    return AvailableRooms(campus, building, date, time)


def report_unavailable_room(room_id: str, date: datetime.date, time: str, username: str):
    """反馈实际不可用的教室"""
    return UnavailableRoomReport.new(room_id, date, time, reporter=username)


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


def multi_people_schedule(people: List[str], date: datetime.date, current_user: str) -> MultiPeopleSchedule:
    """多人日程展示。输入学号或教工号列表及日期，输出多人在当天的日程。

    返回的第一个参数表示需要授权的用户列表，第二个参数为MultiPeopleSchedule对象。如果部分用户需要授权才能访问，只返回可以访问的师生的时间安排
    """
    return MultiPeopleSchedule(people, date, current_user)

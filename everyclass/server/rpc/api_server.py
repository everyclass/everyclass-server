from dataclasses import dataclass, field, fields
from typing import Dict, List, Set

from flask import current_app as app

from everyclass.server import logger
from everyclass.server.exceptions import RpcException
from everyclass.server.rpc.http import HttpRpc
from everyclass.server.utils.resource_identifier_encrypt import encrypt


def ensure_slots(cls, dct: Dict):
    """移除 dataclass 中不存在的key，预防 dataclass 的 __init__ 中 unexpected argument 的发生。"""
    _names = [x.name for x in fields(cls)]
    _del = []
    for key in dct:
        if key not in _names:
            _del.append(key)
    for key in _del:
        del dct[key]  # delete unexpected keys
        logger.warn("Unexpected field `{}` is removed when converting dict to dataclass `{}`".format(key, cls.__name__))
    return dct


@dataclass
class SearchResultStudentItem:
    sid: str
    name: str
    semesters: List[str]
    deputy: str
    klass: str

    @classmethod
    def make(cls, dct: Dict) -> "SearchResultStudentItem":
        del dct["type"]
        dct['semesters'].sort()
        return cls(**ensure_slots(cls, dct))


@dataclass
class SearchResultTeacherItem:
    tid: str
    name: str
    semesters: List[str]
    deputy: str

    @classmethod
    def make(cls, dct: Dict) -> "SearchResultTeacherItem":
        del dct["type"]
        dct['semesters'].sort()
        return cls(**ensure_slots(cls, dct))


@dataclass
class SearchResultClassroomItem:
    rid: str
    name: str
    semesters: List[str]

    @classmethod
    def make(cls, dct: Dict) -> "SearchResultClassroomItem":
        del dct["type"]
        dct['semesters'].sort()
        return cls(**ensure_slots(cls, dct))


@dataclass
class SearchResult:
    students: List[SearchResultStudentItem]
    teachers: List[SearchResultTeacherItem]
    classrooms: List[SearchResultClassroomItem]

    @classmethod
    def make(cls, data_lst: List) -> "SearchResult":
        students, teachers, classrooms = [], [], []
        for each in data_lst:
            if each["type"] == "student":
                students.append(SearchResultStudentItem.make(each))
            elif each["type"] == "teacher":
                teachers.append(SearchResultTeacherItem.make(each))
            elif each["type"] == "classroom":
                classrooms.append(SearchResultClassroomItem.make(each))
        return cls(students=students, teachers=teachers, classrooms=classrooms)


@dataclass
class TeacherItem:
    teacher_id: str
    teacher_id_encrypted: str
    name: str
    title: str

    @classmethod
    def make(cls, dct: Dict) -> "TeacherItem":
        dct['teacher_id_encrypted'] = encrypt('teacher', dct['teacher_id'])
        return cls(**ensure_slots(cls, dct))


@dataclass
class CourseItem:
    name: str
    cid: str
    room: str
    room_id: str
    room_id_encrypted: str
    week: List[int]
    week_string: str
    teachers: List[TeacherItem]

    @classmethod
    def make(cls, dct: Dict) -> "CourseItem":
        # remove duplicated teachers
        tid_set: Set[str] = set()
        unique_teacher_list: List[TeacherItem] = []
        for teacher in dct["teachers"]:
            if teacher["teacher_id"] in tid_set:
                continue
            else:
                tid_set.add(teacher.tid)
                unique_teacher_list.append(teacher)
        dct["teachers"] = unique_teacher_list

        dct['room_id_encrypted'] = encrypt('klass', dct['room_id'])
        return cls(**ensure_slots(cls, dct))


@dataclass
class ClassroomTimetableResult:
    room_id: str
    room_id_encrypted: str
    name: str
    building: str
    campus: str
    semester: str
    courses: List[CourseItem]

    @classmethod
    def make(cls, dct: Dict) -> "ClassroomTimetableResult":
        del dct["status"]
        dct['semesters'].sort()
        dct['room_id_encrypted'] = encrypt('room', dct['room_id'])
        return cls(**ensure_slots(cls, dct))


@dataclass
class CourseResultTeacherItem:
    name: str
    tid: str
    title: str
    unit: str

    @classmethod
    def make(cls, dct: Dict) -> "CourseResultTeacherItem":
        return cls(**ensure_slots(cls, dct))


@dataclass
class CourseResultStudentItem:
    name: str
    sid: str
    sid_encrypted: str
    klass: str
    deputy: str

    @classmethod
    def make(cls, dct: Dict) -> "CourseResultStudentItem":
        dct["klass"] = dct.pop("class")
        dct["sid_encrypted"] = encrypt("student", dct["sid"])
        return cls(**ensure_slots(cls, dct))


@dataclass
class StudentTimetableResult:
    name: str
    student_id: str
    student_id_encrypted: str
    deputy: str
    klass: str
    courses: List[CourseItem]
    semesters: List[str] = field(default_factory=list)  # optional field

    @classmethod
    def make(cls, dct: Dict) -> "StudentTimetableResult":
        del dct["status"]
        dct["courses"] = [CourseItem.make(x) for x in dct["courses"]]
        dct["sid_encrypted"] = encrypt("student", dct["sid"])
        dct["klass"] = dct.pop("class")
        return cls(**dct)


@dataclass
class TeacherTimetableResult:
    name: str
    title: str
    unit: str
    courses: List[CourseItem]
    semesters: List[str] = field(default_factory=list)  # optional field

    @classmethod
    def make(cls, dct: Dict) -> "TeacherTimetableResult":
        del dct["status"]
        dct["courses"] = [CourseItem.make(x) for x in dct["courses"]]
        return cls(**dct)


@dataclass
class CourseResult:
    name: str
    course_id: str
    course_id_encrypted: str
    union_name: str
    hour: int
    lesson: str
    type: str
    pick_num: int
    rid: str
    room: str
    students: List[CourseResultStudentItem]
    teachers: List[CourseResultTeacherItem]
    week: List[int]
    week_string: str

    @classmethod
    def make(cls, dct: Dict) -> "CourseResult":
        del dct["status"]
        dct["teachers"] = [CourseResultTeacherItem.make(x) for x in dct["teachers"]]
        dct["students"] = [CourseResultStudentItem.make(x) for x in dct["students"]]
        dct["course_id_encrypted"] = encrypt("klass", dct["course_id"])
        return cls(**ensure_slots(cls, dct))


def teacher_list_to_str(teachers: List[CourseResultTeacherItem]) -> str:
    """CourseResultTeacherItem 列表转换为老师列表字符串"""
    string = ''
    for teacher in teachers:
        string = string + teacher.name + teacher.title + '、'
    return string[:len(string) - 1]


class APIServer:
    @classmethod
    def search(cls, keyword: str) -> SearchResult:
        """在 API Server 上搜索

        :param keyword: 需要搜索的关键词
        :return: 搜索结果列表
        """
        resp = HttpRpc.call(method="GET",
                            url='{}/v2/search/{}'.format(app.config['API_SERVER_BASE_URL'], keyword.replace("/", "")),
                            retry=True)
        if resp["status"] != "success":
            raise RpcException('API Server returns non-success status')
        search_result = SearchResult.make(resp["data"])
        return search_result

    @classmethod
    def get_student(cls, student_id: str, semester: str):
        """
        根据学期和教工号获得学生课表

        :param student_id: 学号
        :param semester: 学期，如 2018-2019-1
        :return:
        """
        resp = HttpRpc.call(method="GET",
                            url='{}/v2/student/{}/timetable/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                       student_id,
                                                                       semester),
                            retry=True)
        if resp["status"] != "success":
            raise RpcException('API Server returns non-success status')
        search_result = StudentTimetableResult.make(resp)
        return search_result

    @classmethod
    def get_teacher_timetable(cls, teacher_id: str, semester: str):
        """
        根据学期和教工号获得老师课表

        :param teacher_id: 教工号
        :param semester: 学期，如 2018-2019-1
        :return:
        """
        resp = HttpRpc.call(method="GET",
                            url='{}/v2/teacher/{}/timetable/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                       teacher_id,
                                                                       semester),
                            retry=True)
        if resp["status"] != "success":
            raise RpcException('API Server returns non-success status')
        search_result = TeacherTimetableResult.make(resp)
        return search_result

    @classmethod
    def get_classroom_timetable(cls, semester: str, room_id: str):
        """
        根据学期和教室ID获得教室课表
        :param semester: 学期，如 2018-2019-1
        :param room_id: 教室ID
        :return:
        """
        resp = HttpRpc.call(method="GET",
                            url='{}/v2/room/{}/timetable/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                    room_id,
                                                                    semester),
                            retry=True)
        if resp["status"] != "success":
            raise RpcException('API Server returns non-success status')
        search_result = ClassroomTimetableResult.make(resp)
        return search_result

    @classmethod
    def get_course(cls, semester: str, course_id: str) -> CourseResult:
        """
        根据学期和课程ID获得课程
        :param semester: 学期，如 2018-2019-1
        :param course_id: 课程ID
        :return:
        """
        resp = HttpRpc.call(method="GET",
                            url='{}/v2/course/{}/{}'.format(app.config['API_SERVER_BASE_URL'], semester, course_id),
                            retry=True)
        if resp["status"] != "success":
            raise RpcException('API Server returns non-success status')
        search_result = CourseResult.make(resp)
        return search_result

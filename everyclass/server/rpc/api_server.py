from dataclasses import dataclass, field, fields
from typing import Dict, List

from flask import current_app as app

from everyclass.server import logger
from everyclass.server.exceptions import RpcException
from everyclass.server.rpc.http import HttpRpc


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
class ClassroomResultCourseItemTeacherItem:
    tid: str
    name: str
    title: str

    @classmethod
    def make(cls, dct: Dict) -> "ClassroomResultCourseItemTeacherItem":
        return cls(**ensure_slots(cls, dct))


@dataclass
class ClassroomResultCourseItem:
    name: str
    cid: str
    room: str
    rid: str
    week: List[int]
    week_string: str
    teacher: List[ClassroomResultCourseItemTeacherItem]

    @classmethod
    def make(cls, dct: Dict) -> "ClassroomResultCourseItem":
        dct["teachers"] = [ClassroomResultCourseItemTeacherItem.make(x) for x in dct["teacher"]]
        return cls(**ensure_slots(cls, dct))


@dataclass
class ClassroomTimetableResult:
    rid: str
    name: str
    building: str
    campus: str
    semester: str
    courses: List[ClassroomResultCourseItem]

    @classmethod
    def make(cls, dct: Dict) -> "ClassroomTimetableResult":
        del dct["status"]
        dct['semesters'].sort()
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
    klass: str
    deputy: str

    @classmethod
    def make(cls, dct: Dict) -> "CourseResultStudentItem":
        dct["klass"] = dct.pop("class")
        return cls(**ensure_slots(cls, dct))


@dataclass
class CourseResult:
    name: str
    cid: str
    union_class_name: str
    hour: int
    lesson: str
    type: str
    pick_num: int
    rid: str
    room: str
    students: List[CourseResultStudentItem]
    teachers: List[CourseResultTeacherItem]
    week: List[int]
    week_string: str = field(default="")  # optional field

    @classmethod
    def make(cls, dct: Dict) -> "CourseResult":
        del dct["status"]
        dct["teachers"] = [CourseResultTeacherItem.make(x) for x in dct["teacher"]]
        del dct["teacher"]
        dct["students"] = [CourseResultStudentItem.make(x) for x in dct["student"]]
        del dct["student"]
        dct["union_class_name"] = dct.pop("klass")
        dct["pick_num"] = dct.pop("pick")
        return cls(**ensure_slots(cls, dct))


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
    def get_student(cls, sid: str):
        pass

    @classmethod
    def get_teacher(cls, tid: str):
        pass

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

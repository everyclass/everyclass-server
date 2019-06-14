from dataclasses import dataclass, field, fields
from typing import Dict, List

from flask import current_app as app

from everyclass.rpc.http import HttpRpc
from everyclass.server import logger
from everyclass.server.config import get_config
from everyclass.server.exceptions import RpcException
from everyclass.server.utils import weeks_to_string
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
    student_id: str
    student_id_encoded: str
    name: str
    semesters: List[str]
    deputy: str
    klass: str
    pattern: str

    @classmethod
    def make(cls, dct: Dict) -> "SearchResultStudentItem":
        dct['semesters'] = sorted(dct.pop("semester_list"))
        dct['student_id'] = dct.pop("student_code")  # rename
        dct['student_id_encoded'] = encrypt('student', dct['student_id'])
        dct['klass'] = dct.pop("class")
        del dct["type"]
        return cls(**ensure_slots(cls, dct))


@dataclass
class SearchResultTeacherItem:
    teacher_id: str
    teacher_id_encoded: str
    name: str
    semesters: List[str]
    unit: str
    title: str
    pattern: str

    @classmethod
    def make(cls, dct: Dict) -> "SearchResultTeacherItem":
        dct['semesters'] = sorted(dct.pop("semester_list"))
        dct['teacher_id'] = dct.pop("teacher_code")  # rename
        dct['teacher_id_encoded'] = encrypt('teacher', dct['teacher_id'])
        del dct["type"]
        return cls(**ensure_slots(cls, dct))


@dataclass
class SearchResultClassroomItem:
    room_id: str
    room_id_encoded: str
    name: str
    semesters: List[str]
    campus: str
    building: str
    pattern: str  # 搜索结果来源

    @classmethod
    def make(cls, dct: Dict) -> "SearchResultClassroomItem":
        dct['semesters'] = sorted(dct.pop("semester_list"))
        dct['room_id'] = dct.pop("room_code")  # rename
        dct['room_id_encoded'] = encrypt('room', dct['room_id'])
        del dct["type"]
        return cls(**ensure_slots(cls, dct))


@dataclass
class SearchResult:
    students: List[SearchResultStudentItem]
    teachers: List[SearchResultTeacherItem]
    classrooms: List[SearchResultClassroomItem]

    @classmethod
    def make(cls, dct: Dict) -> "SearchResult":
        del dct["status"]
        del dct["info"]
        dct["students"] = [SearchResultStudentItem.make(x) for x in dct['data'] if
                           'type' in x and x['type'] == 'student']
        dct["teachers"] = [SearchResultTeacherItem.make(x) for x in dct['data'] if
                           'type' in x and x['type'] == 'teacher']
        dct["classrooms"] = [SearchResultClassroomItem.make(x) for x in dct['data'] if
                             'type' in x and x['type'] == 'room']
        dct.pop("data")

        return cls(**ensure_slots(cls, dct))

    def append(self, to_append: Dict):
        """对于多页搜索结果，将第一页之后的结果追加到搜索结果对象"""
        new_result = self.__class__.make(to_append)
        self.students.extend(new_result.students)
        self.teachers.extend(new_result.teachers)
        self.classrooms.extend(new_result.classrooms)


@dataclass
class TeacherItem:
    teacher_id: str
    teacher_id_encoded: str
    name: str
    title: str

    @classmethod
    def make(cls, dct: Dict) -> "TeacherItem":
        dct['teacher_id'] = dct.pop("teacher_code")
        dct['teacher_id_encoded'] = encrypt('teacher', dct['teacher_id'])
        return cls(**ensure_slots(cls, dct))


@dataclass
class CardItem:
    name: str
    card_id: str
    card_id_encoded: str
    room: str
    room_id: str
    room_id_encoded: str
    weeks: List[int]
    week_string: str
    lesson: str
    teachers: List[TeacherItem]
    course_id: str

    @classmethod
    def make(cls, dct: Dict) -> "CardItem":
        dct["teachers"] = [TeacherItem.make(x) for x in dct.pop("teacher_list")]
        dct['room_id'] = dct.pop('room_code')
        dct['card_id'] = dct.pop('card_code')
        dct['weeks'] = dct.pop('week_list')
        dct['week_string'] = weeks_to_string(dct['weeks'])
        dct['room_id_encoded'] = encrypt('room', dct['room_id'])
        dct['card_id_encoded'] = encrypt('klass', dct['card_id'])
        dct['course_id'] = dct.pop('course_code')
        return cls(**ensure_slots(cls, dct))


@dataclass
class ClassroomTimetableResult:
    room_id: str
    room_id_encoded: str
    name: str
    building: str
    campus: str
    semester: str
    semesters: List[str]
    cards: List[CardItem]

    @classmethod
    def make(cls, dct: Dict) -> "ClassroomTimetableResult":
        del dct["status"]
        dct['semesters'] = sorted(dct.pop('semester_list'))
        dct['room_id'] = dct.pop("room_code")
        dct['cards'] = [CardItem.make(x) for x in dct.pop('card_list')]

        dct['room_id_encoded'] = encrypt('room', dct['room_id'])
        return cls(**ensure_slots(cls, dct))


@dataclass
class CardResultTeacherItem:
    name: str
    teacher_id: str
    teacher_id_encoded: str
    title: str
    unit: str

    @classmethod
    def make(cls, dct: Dict) -> "CardResultTeacherItem":
        dct['teacher_id'] = dct.pop('teacher_code')
        dct['teacher_id_encoded'] = encrypt('teacher', dct['teacher_id'])
        return cls(**ensure_slots(cls, dct))


@dataclass
class CardResultStudentItem:
    name: str
    student_id: str
    student_id_encoded: str
    klass: str
    deputy: str

    @classmethod
    def make(cls, dct: Dict) -> "CardResultStudentItem":
        dct["klass"] = dct.pop("class")
        dct["student_id"] = dct.pop("student_code")
        dct["student_id_encoded"] = encrypt("student", dct.get("student_id"))
        return cls(**ensure_slots(cls, dct))


@dataclass
class StudentResult:
    name: str
    student_id: str
    student_id_encoded: str
    campus: str
    deputy: str
    klass: str
    semesters: List[str] = field(default_factory=list)  # optional field

    @classmethod
    def make(cls, dct: Dict) -> "StudentResult":
        del dct["status"]
        dct["student_id"] = dct.pop("student_code")
        dct["student_id_encoded"] = encrypt("student", dct["student_id"])
        dct["klass"] = dct.pop("class")
        dct["semesters"] = dct.pop('semester_list')
        return cls(**ensure_slots(cls, dct))


@dataclass
class StudentTimetableResult:
    name: str  # 姓名
    student_id: str  # 学号
    student_id_encoded: str  # 编码后的学号
    campus: str  # 所在校区
    deputy: str  # 院系
    klass: str  # 班级
    cards: List[CardItem]  # card 列表
    semester: str  # 当前学期
    semesters: List[str] = field(default_factory=list)  # 学期列表

    @classmethod
    def make(cls, dct: Dict) -> "StudentTimetableResult":
        del dct["status"]
        dct["cards"] = [CardItem.make(x) for x in dct.pop("card_list")]
        dct["semesters"] = dct.pop("semester_list")
        dct["student_id"] = dct.pop("student_code")
        dct["student_id_encoded"] = encrypt("student", dct["student_id"])
        dct["klass"] = dct.pop("class")
        return cls(**ensure_slots(cls, dct))


@dataclass
class TeacherTimetableResult:
    name: str  # 姓名
    teacher_id: str  # 教工号
    teacher_id_encoded: str  # 编码后的教工号
    degree: str  # 教师学历（可能为空）
    title: str  # 职称
    unit: str  # 所在单位
    cards: List[CardItem]  # card 列表
    semester: str  # 当前学期
    semesters: List[str] = field(default_factory=list)  # 所有学期

    @classmethod
    def make(cls, dct: Dict) -> "TeacherTimetableResult":
        del dct["status"]
        dct["cards"] = [CardItem.make(x) for x in dct.pop("card_list")]
        dct['semesters'] = sorted(dct.pop('semester_list'))
        dct['teacher_id'] = dct.pop('teacher_code')
        dct["teacher_id_encoded"] = encrypt("teacher", dct["teacher_id"])
        return cls(**ensure_slots(cls, dct))


@dataclass
class CardResult:
    name: str  # 课程名
    card_id: str  # card id
    card_id_encoded: str  # 编码后的 card id
    semester: str  # 学期
    union_name: str  # 合班（教学班）名称
    hour: int  # 课时
    lesson: str  # 上课时间，如10506
    type: str  # 课程类型
    picked: int  # 选课人数
    room: str  # 教室名
    room_id: str  # 教室 ID
    room_id_encoded: str  # 编码后的教室 ID
    students: List[CardResultStudentItem]  # 学生列表
    teachers: List[CardResultTeacherItem]  # 老师列表
    weeks: List[int]  # 周次列表
    week_string: str  # 周次字符串表示
    course_id: str  # 课程 ID

    @classmethod
    def make(cls, dct: Dict) -> "CardResult":
        del dct["status"]
        dct["teachers"] = [CardResultTeacherItem.make(x) for x in dct.pop("teacher_list")]
        dct["students"] = [CardResultStudentItem.make(x) for x in dct.pop("student_list")]
        dct['card_id'] = dct.pop('card_code')
        dct["card_id_encoded"] = encrypt("klass", dct["card_id"])
        dct['room_id'] = dct.pop('room_code')
        dct['room_id_encoded'] = encrypt("room", dct["room_id"])
        dct['weeks'] = dct.pop("week_list")
        dct['week_string'] = weeks_to_string(dct['weeks'])
        dct['course_id'] = dct.pop('course_code')
        dct['union_name'] = dct.pop('tea_class')
        return cls(**ensure_slots(cls, dct))


def teacher_list_to_name_str(teachers: List[CardResultTeacherItem]) -> str:
    """CardResultTeacherItem 列表转换为老师姓名列表字符串"""
    return "、".join([t.name + t.title for t in teachers])


def teacher_list_to_tid_str(teachers: List[CardResultTeacherItem]) -> str:
    """CardResultTeacherItem 列表转换为排序的教工号列表字符串"""
    return ";".join(sorted([t.teacher_id for t in teachers]))


class APIServer:
    @classmethod
    def search(cls, keyword: str) -> SearchResult:
        """在 API Server 上搜索

        :param keyword: 需要搜索的关键词
        :return: 搜索结果列表
        """
        keyword = keyword.replace("/", "")

        resp = HttpRpc.call(method="GET",
                            url='{}/search/query?key={}&page_size={}'.format(app.config['API_SERVER_BASE_URL'],
                                                                             keyword,
                                                                             100),
                            retry=True,
                            headers={'X-Auth-Token': get_config().API_SERVER_TOKEN})
        if resp["status"] != "success":
            raise RpcException('API Server returns non-success status')
        page_num = resp['info']['page_num']
        search_result = SearchResult.make(resp)

        # 多页结果
        if page_num > 1:
            for page_index in range(2, page_num + 1):
                resp = HttpRpc.call(method="GET",
                                    url='{}/search/query?key={}&page_size={}&page_index={}'.format(
                                            app.config['API_SERVER_BASE_URL'],
                                            keyword,
                                            100, page_index),
                                    retry=True,
                                    headers={'X-Auth-Token': get_config().API_SERVER_TOKEN})
                if resp["status"] != "success":
                    raise RpcException('API Server returns non-success status')
                search_result.append(resp)

        return search_result

    @classmethod
    def get_student(cls, student_id: str):
        """
        根据学号获得学生课表

        :param student_id: 学号
        :return:
        """
        resp = HttpRpc.call(method="GET",
                            url='{}/student/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                       student_id),
                            retry=True,
                            headers={'X-Auth-Token': get_config().API_SERVER_TOKEN})
        if resp["status"] != "success":
            raise RpcException('API Server returns non-success status')
        search_result = StudentResult.make(resp)
        return search_result

    @classmethod
    def get_student_timetable(cls, student_id: str, semester: str):
        """
        根据学期和学号获得学生课表

        :param student_id: 学号
        :param semester: 学期，如 2018-2019-1
        :return:
        """
        resp = HttpRpc.call(method="GET",
                            url='{}/student/{}/timetable/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                    student_id,
                                                                    semester),
                            retry=True,
                            headers={'X-Auth-Token': get_config().API_SERVER_TOKEN})
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
                            url='{}/teacher/{}/timetable/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                    teacher_id,
                                                                    semester),
                            retry=True,
                            headers={'X-Auth-Token': get_config().API_SERVER_TOKEN})
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
                            url='{}/room/{}/timetable/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                 room_id,
                                                                 semester),
                            retry=True,
                            headers={'X-Auth-Token': get_config().API_SERVER_TOKEN})
        if resp["status"] != "success":
            raise RpcException('API Server returns non-success status')
        search_result = ClassroomTimetableResult.make(resp)
        return search_result

    @classmethod
    def get_card(cls, semester: str, card_id: str) -> CardResult:
        """
        根据学期和card ID获得card
        :param semester: 学期，如 2018-2019-1
        :param card_id: card ID
        :return:
        """
        resp = HttpRpc.call(method="GET",
                            url='{}/card/{}/timetable/{}'.format(app.config['API_SERVER_BASE_URL'], card_id,
                                                                 semester),
                            retry=True,
                            headers={'X-Auth-Token': get_config().API_SERVER_TOKEN})
        if resp["status"] != "success":
            raise RpcException('API Server returns non-success status')
        search_result = CardResult.make(resp)
        return search_result

from dataclasses import dataclass, field, fields
from typing import Dict, List, Tuple, Union

from flask import current_app as app

from everyclass.rpc import RpcException
from everyclass.rpc.http import HttpRpc


def encrypt(resource_type: str, resource_id: str):
    """资源加密函数的代理，当rpc模块初始化不指定加密函数时，返回待加密的原值"""
    from everyclass.rpc import _resource_id_encrypt
    if _resource_id_encrypt:
        return _resource_id_encrypt(resource_type, resource_id)
    else:
        return resource_id


def ensure_slots(cls, dct: Dict):
    """移除 dataclass 中不存在的key，预防 dataclass 的 __init__ 中 unexpected argument 的发生。"""
    _names = [x.name for x in fields(cls)]
    _del = []
    for key in dct:
        if key not in _names:
            _del.append(key)
    for key in _del:
        del dct[key]  # delete unexpected keys
        from everyclass.rpc import _logger
        _logger.warn(
                "Unexpected field `{}` is removed when converting dict to dataclass `{}`".format(key, cls.__name__))
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
                            headers={'X-Auth-Token': app.config['API_SERVER_TOKEN']})
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
                                    headers={'X-Auth-Token': app.config['API_SERVER_TOKEN']})
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
                            headers={'X-Auth-Token': app.config['API_SERVER_TOKEN']})
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
                            headers={'X-Auth-Token': app.config['API_SERVER_TOKEN']})
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
                            headers={'X-Auth-Token': app.config['API_SERVER_TOKEN']})
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
                            headers={'X-Auth-Token': app.config['API_SERVER_TOKEN']})
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
                            headers={'X-Auth-Token': app.config['API_SERVER_TOKEN']})
        if resp["status"] != "success":
            raise RpcException('API Server returns non-success status')
        search_result = CardResult.make(resp)
        return search_result


def weeks_to_string(original_weeks: List[int]) -> str:
    """
    获得周次列表的字符串表示（鉴于 API Server 转换的效果不好，暂时在本下游服务进行转换）

    :param original_weeks: int 类型的 list，每一个数字代表一个周次
    :return: 周次的字符串表示
    """

    def odd(num: int) -> bool:
        return num % 2 == 1

    def int_type_to_string(typ: int) -> str:
        if typ == 0:
            return "/周"
        elif typ == 1:
            return "/单周"
        elif typ == 2:
            return "/双周"
        else:
            raise ValueError("Unknown week type")

    processed_weeks: List[Tuple[int, int, int]] = []
    current_start = original_weeks[0]
    current_end: Union[int, None] = None
    current_type: Union[int, None] = None

    for i, _ in enumerate(original_weeks):
        # 当前是最后一个元素
        if i == len(original_weeks) - 1:
            processed_weeks.append((current_start,
                                    current_end if current_end else current_start,
                                    current_type if current_type else 0))
            break

        # 存在下一个元素且 current_type 为空（说明当前子序列的第一个元素），则判断当前周次类型
        # 根据当前元素和下一个元素判断周次类型并保存到 current_type
        if current_type is None:
            if original_weeks[i + 1] == original_weeks[i] + 1:  # 间隔一周
                current_type = 0
            elif original_weeks[i + 1] == original_weeks[i] + 2:  # 间隔两周
                current_type = 1 if odd(current_start) else 2
            else:
                # 间隔大于两周（如：[1, 5]），拆分
                processed_weeks.append((current_start, current_start, 0))
                current_start = original_weeks[i + 1]
                current_end = None
                current_type = None
                continue

        # 有下一个元素且当前子序列已经有类型（current_type），判断下一个元素是否符合当前周类型的要求，如能则拓展子序列，不能则分割子序列
        if current_type == 0:
            if original_weeks[i + 1] == original_weeks[i] + 1:
                current_end = original_weeks[i + 1]
            else:
                # 结合具体流程可知 current_end 为 int 类型，但 flake8 把它识别为 Optional[int]，导致报错
                processed_weeks.append((current_start, current_end, current_type))  # noqa: T484
                current_start = original_weeks[i + 1]
                current_end = None
                current_type = None
        else:
            if original_weeks[i + 1] == original_weeks[i] + 2:
                current_end = original_weeks[i + 1]
            else:
                processed_weeks.append((current_start, current_end, current_type))  # noqa: T484
                current_start = original_weeks[i + 1]
                current_end = None
                current_type = None

    # 检查所有周是否都是单周、都是双周或者都是全周
    # 是则采用类似于 “1-3, 7-9/单周” 的精简表示，否则采用类似于 “1-3/单周, 4-8/双周” 的表示
    week_type: Union[int, None] = None
    week_type_consistent = True
    for week in processed_weeks:
        if week_type is None:
            week_type = week[2]
        if week[2] != week_type:
            week_type_consistent = False

    weeks_str = ""
    if week_type_consistent:
        for week in processed_weeks:
            if week[0] == week[1]:
                weeks_str += "{}, ".format(week[0])
            else:
                weeks_str += "{}-{}, ".format(week[0], week[1])
        weeks_str = weeks_str[:len(weeks_str) - 2] + int_type_to_string(processed_weeks[0][2])
    else:
        for week in processed_weeks:
            if week[0] == week[1]:
                weeks_str += "{}{}, ".format(week[0], int_type_to_string(week[2]))
            else:
                weeks_str += "{}-{}{}, ".format(week[0], week[1], int_type_to_string(week[2]))
        weeks_str = weeks_str[:len(weeks_str) - 2]

    # 如果原始表示字数更短，切换到原始表示
    plain = ", ".join([str(x) for x in original_weeks]) + int_type_to_string(0)
    if len(plain) < len(weeks_str):
        weeks_str = plain

    return weeks_str

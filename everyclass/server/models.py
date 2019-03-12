import re
from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple


class Semester(object):
    def __init__(self, para):
        """
        构造函数，接收一个 tuple (2016,2017,2) 或者学期字符串"2016-2017-2"
        """
        # Semester("2016-2017-2")
        if isinstance(para, str) and re.match(r'\d{4}-\d{4}-\d', para):
            self.year1 = int(para[0:4])
            self.year2 = int(para[5:9])
            self.sem = int(para[10])

        # Semester("16-17-2")
        elif isinstance(para, str) and re.match(r'\d{2}-\d{2}-\d', para):
            self.year1 = int(para[0:2]) + 2000
            self.year2 = int(para[3:5]) + 2000
            self.sem = int(para[6])

        # Semester((2016,2017,2))
        elif isinstance(para, tuple):
            self.year1 = int(para[0])
            self.year2 = int(para[1])
            self.sem = int(para[2])

        # illegal
        else:
            self.year1 = 2020
            self.year2 = 2021
            self.sem = 1

    def __repr__(self):
        return '<Semester {}-{}-{}>'.format(self.year1, self.year2, self.sem)

    def __str__(self):
        return '{}-{}-{}'.format(self.year1, self.year2, self.sem)

    def __eq__(self, other):
        if not isinstance(other, Semester):
            other = Semester(other)
        return self.year1 == other.year1 and self.year2 == other.year2 and self.sem == other.sem

    def to_tuple(self):
        return self.year1, self.year2, self.sem

    def to_str(self, simplify=False):
        """
        因为to_string的参数一定来自程序内部，所以不检查有效性

        :param simplify: True if you want short str
        :return: str like '16-17-2' if simplify==True, '2016-2017-2' is simplify==False
        """
        if not simplify:
            # return like '2016-2017-2'
            return str(self.year1) + '-' + str(self.year2) + '-' + str(self.sem)
        else:
            # return like '16-17-2'
            return str(self.year1)[2:4] + '-' + str(self.year2)[2:4] + '-' + str(self.sem)

    def to_db_code(self):
        """
        获取用于数据表命名的学期，如 16_17_2
        """
        return self.to_str(simplify=True).replace('-', '_')


class Student(NamedTuple):
    sid_orig: str
    sid: str
    name: str


@dataclass
class RPCStudentResult:
    class_: str
    deputy: str
    name: str
    semesters: List[str]
    sid: str

    @classmethod
    def make(cls, dct: Dict) -> "RPCStudentResult":
        dct["class_"] = dct.pop("class")
        dct["semesters"] = [RPCCourseInSemesterItem.make(x) for x in dct["semester"]]
        del dct["semester"]
        return cls(**dct)


@dataclass
class RPCTeacherInCourseItem:
    name: str
    tid: str
    title: str


@dataclass
class RPCCourseInSemesterItem:
    cid: str
    lesson: str
    name: str
    rid: str
    room: str
    week: List[int]
    teachers: List[RPCTeacherInCourseItem]
    week_string: str = field(default="")  # optional field

    @classmethod
    def make(cls, dct: Dict) -> "RPCCourseInSemesterItem":
        dct["teachers"] = [RPCTeacherInCourseItem(**x) for x in dct["teacher"]]
        del dct["teacher"]
        return cls(**dct)


@dataclass
class RPCStudentInSemesterResult:
    name: str
    sid: str  # 学号
    deputy: str
    class_: str
    courses: List[RPCCourseInSemesterItem]
    semester_list: List[str] = field(default_factory=list)  # optional field

    @classmethod
    def make(cls, dct: Dict) -> "RPCStudentInSemesterResult":
        dct["class_"] = dct.pop("class")
        dct["courses"] = [RPCCourseInSemesterItem.make(x) for x in dct["course"]]
        del dct["course"]
        return cls(**dct)


@dataclass
class RPCTeacherInSemesterResult:
    name: str
    tid: str  # 教工号
    title: str
    unit: str
    courses: List[RPCCourseInSemesterItem]
    semester_list: List[str] = field(default_factory=list)  # optional field

    @classmethod
    def make(cls, dct: Dict) -> "RPCTeacherInSemesterResult":
        dct["courses"] = [RPCCourseInSemesterItem.make(x) for x in dct["course"]]
        del dct["course"]
        return cls(**dct)


@dataclass
class RPCRoomResult:
    name: str
    rid: str
    building: str
    campus: str
    courses: List[RPCCourseInSemesterItem]
    semester_list: List[str] = field(default_factory=list)  # optional field

    @classmethod
    def make(cls, dct: Dict) -> "RPCRoomResult":
        dct["courses"] = [RPCCourseInSemesterItem.make(x) for x in dct["course"]]
        del dct["course"]
        return cls(**dct)


@dataclass
class RPCStudentInCourseItem:
    name: str
    sid: str
    class_: str
    deputy: str


@dataclass
class RPCCourseResult:
    name: str
    cid: str
    union_class_name: str
    hour: int
    lesson: str
    type: str
    pick_num: int
    rid: str
    room: str
    students: List[RPCStudentInCourseItem]
    teachers: List[RPCTeacherInCourseItem]
    week: List[int]
    week_string: str = field(default="")  # optional field

    @classmethod
    def make(cls, dct: Dict) -> "RPCCourseResult":
        dct["teachers"] = [RPCTeacherInCourseItem(**x) for x in dct["teacher"]]
        del dct["teacher"]
        dct["students"] = [RPCTeacherInCourseItem(**x) for x in dct["student"]]
        del dct["student"]
        return cls(**dct)

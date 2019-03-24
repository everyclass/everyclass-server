from dataclasses import dataclass
from typing import Dict, List, Union

from flask import current_app as app

from everyclass.server.exceptions import RpcException
from everyclass.server.rpc.http import HttpRpc


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
        return cls(**dct)


@dataclass
class SearchResultTeacherItem:
    tid: str
    name: str
    semesters: List[str]
    deputy: str

    @classmethod
    def make(cls, dct: Dict) -> "SearchResultTeacherItem":
        del dct["type"]
        return cls(**dct)


@dataclass
class SearchResultClassroomItem:
    rid: str
    name: str
    semesters: List[str]

    @classmethod
    def make(cls, dct: Dict) -> "SearchResultClassroomItem":
        del dct["type"]
        return cls(**dct)


@dataclass
class SearchResult:
    lst: List[Union[SearchResultStudentItem, SearchResultTeacherItem, SearchResultClassroomItem]]

    @classmethod
    def make(cls, data_lst: List) -> "SearchResult":
        lst = []
        for each in data_lst:
            if each["type"] == "student":
                lst.append(SearchResultStudentItem.make(each))
            elif each["type"] == "teacher":
                lst.append(SearchResultTeacherItem.make(each))
            elif each["type"] == "classroom":
                lst.append(SearchResultClassroomItem.make(each))
        return cls(*lst)


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
    def get_student(cls, xh: str):
        pass

    @classmethod
    def get_teacher(cls, jgh: str):
        pass

    @classmethod
    def get_classroom(cls, room_id: str):
        pass

    @classmethod
    def get_course(cls, course_id: str):
        pass

from typing import Tuple, Union

from everyclass.rpc.entity import SearchResultStudentItem, SearchResultTeacherItem, Entity


class PeopleNotFoundError(ValueError):
    pass


def get_people_info(identifier: str) -> Tuple[bool, Union[SearchResultStudentItem, SearchResultTeacherItem]]:
    """
    query Entity service to get people info

    :param identifier: student ID or teacher ID
    :return: The first parameter is a Union[bool, None]. True means it's a student, False means it's a teacher. If
     the identifier is not found, a PeopleNotFoundError is raised. The second parameter is the info of student or
     teacher.
    """
    result = Entity.search(identifier)
    if len(result.students) > 0:
        return True, result.students[0]
    if len(result.teachers) > 0:
        return False, result.teachers[0]
    raise PeopleNotFoundError

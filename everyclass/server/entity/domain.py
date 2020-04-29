import datetime
from typing import Tuple

from everyclass.rpc.entity import CardItem
from everyclass.server.utils.config import get_config


def get_semester_date(date: datetime.date) -> Tuple[str, int, int]:
    """获取日期对应的学期、所属周次及星期（0表示周日，1表示周一...）

    >>> get_semester_date(datetime.date(2020, 2, 22))
    ('2019-2020-1', 26, 6)

    >>> get_semester_date(datetime.date(2020, 2, 23))
    ('2019-2020-2', 1, 0)
    """
    config = get_config()

    semesters = list(config.AVAILABLE_SEMESTERS.items())
    semesters.sort(key=lambda x: x[0], reverse=True)

    for sem in semesters:
        sem_start_date = datetime.date(*sem[1]["start"])
        if date >= sem_start_date:
            days_delta = (date - sem_start_date).days
            return "-".join([str(x) for x in sem[0]]), days_delta // 7 + 1, days_delta % 7
    raise ValueError("no applicable semester")


def related_lesson_filter(c: CardItem, week: int, day: int) -> bool:
    return week in c.weeks and c.lesson[0] == str(day)

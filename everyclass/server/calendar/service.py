import os
import time
from collections import defaultdict
from typing import Dict, List, Tuple
from typing import Optional

from ddtrace import tracer

from everyclass.common.time import lesson_string_to_tuple
from everyclass.rpc.entity import Entity, teacher_list_to_name_str
from everyclass.server import logger
from everyclass.server.calendar.domain import ics_generator
from everyclass.server.calendar.repo.calendar_token import reset_tokens, find_calendar_token as find_token, insert_calendar_token, \
    update_last_used_time, use_cache
from everyclass.server.models import Semester
from everyclass.server.utils import calendar_dir


def reset_calendar_tokens(student_id: str, typ: Optional[str] = "student") -> None:
    """清空用户的日历token"""
    return reset_tokens(student_id, typ)


def get_calendar_token(resource_type: str, identifier: str, semester: str) -> str:
    """获取一个有效的日历订阅 token。

    如果找到了可用token则直接返回 token。找不到则生成一个再返回 token"""
    if resource_type == "student":
        token_doc = find_token(sid=identifier, semester=semester)
    else:
        token_doc = find_token(tid=identifier, semester=semester)

    if not token_doc:
        if resource_type == "student":
            token = insert_calendar_token(resource_type="student",
                                          identifier=identifier,
                                          semester=semester)
        else:
            token = insert_calendar_token(resource_type="teacher",
                                          identifier=identifier,
                                          semester=semester)
    else:
        token = token_doc['token']
    return token


def find_calendar_token(token: str) -> Optional[Dict]:
    """查找一个token，如果存在，返回token信息，如果不存在，返回None"""
    return find_token(token=token)


def use_calendar_token(token: str) -> None:
    update_last_used_time(token)


SECONDS_IN_ONE_DAY = 60 * 60 * 24


def generate_ics_file(type_: str, identifier: str, semester: str) -> str:
    """生成ics文件并返回文件名"""
    from everyclass.server import statsd  # 需要在这里导入，否则导入的结果是None

    cal_filename = f"{type_}_{identifier}_{semester}.ics"
    cal_full_path = os.path.join(calendar_dir(), cal_filename)
    # 有缓存、且缓存时间小于一天，且不用强刷缓存
    if os.path.exists(cal_full_path) \
            and time.time() - os.path.getmtime(cal_full_path) < SECONDS_IN_ONE_DAY \
            and use_cache(cal_filename):
        logger.info("ics cache hit")
        statsd.increment("calendar.ics.cache.hit")
        return cal_filename
    statsd.increment("calendar.ics.cache.miss")

    # 无缓存、或需要强刷缓存
    with tracer.trace('rpc'):
        # 获得原始学号或教工号
        if type_ == 'student':
            rpc_result = Entity.get_student_timetable(identifier, semester)
        else:
            # teacher
            rpc_result = Entity.get_teacher_timetable(identifier, semester)

        semester = Semester(semester)

        cards: Dict[Tuple[int, int], List[Dict]] = defaultdict(list)
        for card in rpc_result.cards:
            cards[lesson_string_to_tuple(card.lesson)].append(dict(name=card.name,
                                                                   teacher=teacher_list_to_name_str(card.teachers),
                                                                   week=card.weeks,
                                                                   week_string=card.week_string,
                                                                   classroom=card.room,
                                                                   cid=card.card_id_encoded))

    ics_generator.generate(name=rpc_result.name,
                           cards=cards,
                           semester=semester,
                           filename=cal_filename)

    return cal_filename

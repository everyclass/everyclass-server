"""
This is module to generate .ics file. Should follow RFC2445 standard.
https://tools.ietf.org/html/rfc2445
"""
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pytz
from icalendar import Alarm, Calendar, Event, Timezone, TimezoneStandard

from everyclass.server.config import get_config
from everyclass.server.models import Semester
from everyclass.server.utils import get_time

tzc = Timezone()
tzc.add('tzid', 'Asia/Shanghai')
tzc.add('x-lic-location', 'Asia/Shanghai')
tzs = TimezoneStandard()
tzs.add('tzname', 'CST')
tzs.add('dtstart', datetime(1970, 1, 1, 0, 0, 0))
tzs.add('TZOFFSETFROM', timedelta(hours=8))
tzs.add('TZOFFSETTO', timedelta(hours=8))


def generate(name: str, cards: Dict[Tuple[int, int], List[Dict]], semester: Semester) -> str:
    """
    生成 ics 文件并保存到目录

    :param name: 姓名
    :param cards: 参与的课程
    :param semester: 当前导出的学期
    :param ics_token: ics 令牌
    :return: None
    """
    semester_string = semester.to_str(simplify=True)
    semester = semester.to_tuple()

    # 创建 calender 对象
    cal = Calendar()
    cal.add('prodid', '-//Admirable//EveryClass//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('X-WR-CALNAME', name + '的' + semester_string + '课表')
    cal.add('X-WR-TIMEZONE', 'Asia/Shanghai')

    # 时区
    tzc.add_component(tzs)
    cal.add_component(tzc)

    # 创建 events
    for time in range(1, 7):
        for day in range(1, 8):
            if (day, time) in cards:
                for card in cards[(day, time)]:
                    for week in card['week']:
                        dtstart = _get_datetime(week, day, get_time(time)[0], semester)
                        dtend = _get_datetime(week, day, get_time(time)[1], semester)

                        if dtstart.year == 1984:
                            continue

                        cal.add_component(_build_event(card_name=card['name'],
                                                       times=(dtstart, dtend),
                                                       classroom=card['classroom'],
                                                       teacher=card['teacher'],
                                                       week_string=card['week_string'],
                                                       current_week=week,
                                                       cid=card['cid']))
    return cal.to_ical().decode(encoding='utf-8')


def _get_datetime(week: int, day: int, time: Tuple[int, int], semester: Tuple[int, int, int]) -> datetime:
    """
    根据学期、周次、时间，生成 `datetime` 类型的时间

    :param week: 周次
    :param day: 星期
    :param time: 时间tuple（时,分）
    :param semester: 学期
    :return: datetime 类型的时间
    """
    config = get_config()
    tz = pytz.timezone("Asia/Shanghai")
    dt = datetime(*(config.AVAILABLE_SEMESTERS[semester]['start'] + time), tzinfo=tz)  # noqa: T484
    dt += timedelta(days=(week - 1) * 7 + (day - 1))  # 调整到当前周

    if 'adjustments' in config.AVAILABLE_SEMESTERS[semester]:
        ymd = (dt.year, dt.month, dt.day)
        adjustments = config.AVAILABLE_SEMESTERS[semester]['adjustments']
        if ymd in adjustments:
            if adjustments[ymd]['to']:
                # 调课
                dt = dt.replace(year=adjustments[ymd]['to'][0],
                                month=adjustments[ymd]['to'][1],
                                day=adjustments[ymd]['to'][2])
            else:
                # 冲掉的课年份设置为1984，返回之后被抹去
                dt = dt.replace(year=1984)

    return dt


def _build_event(card_name: str, times: Tuple[datetime, datetime], classroom: str, teacher: str, current_week: int,
                 week_string: str, cid: str) -> Event:
    """
    生成 `Event` 对象

    :param card_name: 课程名
    :param times: 开始和结束时间
    :param classroom: 课程地点
    :param teacher: 任课教师
    :return: `Event` 对象
    """

    event = Event()
    event.add('transp', 'TRANSPARENT')
    summary = card_name
    if classroom != 'None':
        summary = card_name + '@' + classroom
        event.add('location', classroom)

    description = week_string
    if teacher != 'None':
        description += '\n教师：' + teacher
    description += '\n由 EveryClass 每课 (https://everyclass.xyz) 导入'

    event.add('summary', summary)
    event.add('description', description)
    event.add('dtstart', times[0])
    event.add('dtend', times[1])
    event.add('last-modified', datetime.now())

    # 使用"cid-当前周"作为事件的超码
    event_sk = cid + '-' + str(current_week)
    event['uid'] = hashlib.md5(event_sk.encode('utf-8')).hexdigest() + '@everyclass.xyz'
    alarm = Alarm()
    alarm.add('action', 'none')
    alarm.add('trigger', datetime(1980, 1, 1, 3, 5, 0))
    event.add_component(alarm)
    return event

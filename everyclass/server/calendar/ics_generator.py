"""
This is module to generate .ics file. Should follow RFC2445 standard.
https://tools.ietf.org/html/rfc2445
"""
import hashlib
from datetime import datetime, timedelta

import pytz
from icalendar import Alarm, Calendar, Event, Timezone, TimezoneStandard

from everyclass.server.config import get_config
from everyclass.server.tools import get_time


def generate(student_name: str, courses, semester_string: str, semester, ics_token=None):
    """
    生成 ics 文件并保存到目录

    :param ics_token: ics token
    :param student_name: 姓名
    :param courses: classes student are taking
    :param semester_string: 学期字符串，显示在日历标题中，如 `17-18-1`
    :param semester: 当前导出的学期，三元组
    :return: True
    """

    # 创建 calender 对象
    cal = Calendar()
    cal.add('prodid', '-//Admirable//EveryClass//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('X-WR-CALNAME', student_name + '的' + semester_string + '课表')
    cal.add('X-WR-TIMEZONE', 'Asia/Shanghai')

    # 时区
    tzc = Timezone()
    tzc.add('tzid', 'Asia/Shanghai')
    tzc.add('x-lic-location', 'Asia/Shanghai')
    tzs = TimezoneStandard()
    tzs.add('tzname', 'CST')
    tzs.add('dtstart', datetime(1970, 1, 1, 0, 0, 0))
    tzs.add('TZOFFSETFROM', timedelta(hours=8))
    tzs.add('TZOFFSETTO', timedelta(hours=8))
    tzc.add_component(tzs)
    cal.add_component(tzc)

    # 创建 events
    for time in range(1, 7):
        for day in range(1, 8):
            if (day, time) in courses:
                for course in courses[(day, time)]:
                    for each_week in course['week']:
                        dur_starting_week = each_week
                        if course['week'] == '双周' and int(dur_starting_week) % 2 != 0:
                            dur_starting_week = str(int(dur_starting_week) + 1)

                        if course['week'] == '单周' and int(dur_starting_week) % 2 == 0:
                            dur_starting_week = str(int(dur_starting_week) + 1)

                        dtstart = __get_datetime(dur_starting_week, day, get_time(time)[0], semester)
                        dtend = __get_datetime(dur_starting_week, day, get_time(time)[1], semester)
                        # 参数：
                        # 课程名称、初次时间[start、end、interval、until、duration]、循环规则、地点、老师、学生 ID
                        cal.add_component(
                                __add_event(course_name=course['name'],
                                            times=(dtstart, dtend),
                                            classroom=course['classroom'],
                                            teacher=course['teacher'],
                                            week_string=course['week_string'],
                                            current_week=each_week,
                                            cid=course['cid']))

    # 写入文件
    import os

    with open(os.path.join(os.path.dirname(__file__),
                           '../../../calendar_files/{}.ics'.format(ics_token)),
              'w') as f:
        f.write(cal.to_ical().decode(encoding='utf-8'))
    return True


def __get_datetime(week, day, time, semester) -> datetime:
    """
    输入周次，星期、时间tuple（时,分），输出datetime类型的时间

    :param week: 周次
    :param day: 星期
    :param time: 时间tuple（时,分）
    :param semester: 学期
    :return: datetime 类型的时间
    """
    return datetime(*get_config().AVAILABLE_SEMESTERS.get(semester)['start'],
                    *time,
                    tzinfo=pytz.timezone("Asia/Shanghai")
                    ) + timedelta(days=(int(week) - 1) * 7 + (int(day) - 1))


def __add_event(course_name, times, classroom, teacher, current_week, week_string, cid) -> Event:
    """
    把 `Event` 对象添加到 `calendar` 对象中

    :param course_name: 课程名
    :param times: 开始和结束时间
    :param classroom: 课程地点
    :param teacher: 任课教师
    :return: `Event` 对象
    """

    event = Event()
    event.add('transp', 'TRANSPARENT')
    summary = course_name
    if classroom != 'None':
        summary = course_name + '@' + classroom
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
    # todo fix last update time?
    event.add_component(alarm)
    return event

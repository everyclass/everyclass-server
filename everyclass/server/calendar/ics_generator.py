"""
This is module to generate .ics file. Should follow RFC2445 standard.
https://tools.ietf.org/html/rfc2445
"""
import re
from datetime import datetime, timedelta

import pytz
from icalendar import Alarm, Calendar, Event

from everyclass.server.config import get_config
from everyclass.server.tools import get_time


def generate(student_id: str, student_name: str, student_classes, semester_string: str, semester):
    """
    生成 ics 文件并保存到目录

    :param student_id: 学号
    :param student_name: 姓名
    :param student_classes: classes student are taking
    :param semester_string: 学期字符串，显示在日历标题中，如 `17-18-1`
    :param semester: 当前导出的学期，三元组
    :return: True
    """

    # 创建 calender 对象
    cal = Calendar()
    cal.add('prodid', '-//Admirable//EveryClass 1.0//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('X-WR-CALNAME', student_name + '的' + semester_string + '学期课表')
    cal.add('X-WR-TIMEZONE', 'Asia/Shanghai')
    # 创建 events
    for time in range(1, 7):
        for day in range(1, 8):
            if (day, time) in student_classes:
                for every_class in student_classes[(day, time)]:
                    # 每一节课
                    durations = re.split(r',', every_class['duration'])
                    for each_duration in durations:
                        # 每一段上课周
                        if len(re.findall(r'\d{1,2}', each_duration)) == 1:  # 仅当周
                            dur_starting_week = dur_ending_week = re.findall(r'\d{1,2}', each_duration)[0]
                        else:  # X 到 X 周
                            dur_starting_week, dur_ending_week = re.findall(r'\d{1,2}', each_duration)
                        if every_class['week'] == '周':
                            interval = 1
                        else:
                            interval = 2
                        if every_class['week'] == '双周' and int(dur_starting_week) % 2 != 0:
                            dur_starting_week = str(int(dur_starting_week) + 1)

                        if every_class['week'] == '单周' and int(dur_starting_week) % 2 == 0:
                            dur_starting_week = str(int(dur_starting_week) + 1)

                        dtstart = __get_datetime(dur_starting_week, day, get_time(time)[0], semester)
                        dtend = __get_datetime(dur_starting_week, day, get_time(time)[1], semester)
                        until = __get_datetime(dur_ending_week, day, get_time(time)[1], semester) + timedelta(days=1)
                        # 参数：课程名称、初次时间[start、end、interval、until、duration]、循环规则、地点、老师、学生 ID
                        cal.add_component(
                                __add_event(name=every_class['name'],
                                            times=[dtstart, dtend, interval, until, each_duration, every_class['week']],
                                            location=every_class['location'],
                                            teacher=every_class['teacher'],
                                            student_id=student_id))

    # 写入文件
    import os
    with open(os.path.join(os.path.dirname(__file__),
                           '../../../calendar_files/%s-%s.ics' % (student_id, semester_string)),
              'w') as f:
        f.write(cal.to_ical().decode(encoding='utf-8'))

    return True


def batch_generate():
    """生成当前学期所有学生的 ics 文件，每次更新当前学期数据后使用"""
    from everyclass.server import create_app
    from everyclass.server.db.dao import get_all_students, get_classes_for_student
    from everyclass.server.db.model import Semester

    config = get_config()
    now_semester = Semester(config.DEFAULT_SEMESTER)
    now_semester_str = str(now_semester)

    with create_app(offline=True).app_context():
        students = get_all_students()
        print("Total {} students".format(len(students)))
        for each in students:
            if now_semester_str in each[2]:
                print("Generate .ics for [{}]{}...".format(each[0], each[1]))
                student_classes = get_classes_for_student(each[0], now_semester)
                generate(student_id=each[0],
                         student_name=each[1],
                         student_classes=student_classes,
                         semester_string=now_semester.to_str(simplify=True),
                         semester=now_semester.to_tuple())
        print("Done.")


def __get_datetime(week, day, time, semester):
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


def __add_event(name, times, location, teacher, student_id):
    """
    把 `Event` 对象添加到 `calendar` 对象中

    :param name: 课程名
    :param times: 开始和结束时间
    :param location: 课程地点
    :param teacher: 任课教师
    :param student_id: 学号
    :return: `Event` 对象
    """

    event = Event()
    event.add('transp', 'TRANSPARENT')
    summary = name
    if location != 'None':
        summary = name + '@' + location
        event.add('location', location)
    description = times[4] + times[5]
    if teacher != 'None':
        description += '\n教师：' + teacher + '\n'
    description += '由 EveryClass 每课 (https://every.admirable.one) 导入'
    event.add('summary', summary)
    event.add('description', description)
    event.add('dtstart', times[0])
    event.add('dtend', times[1])
    event.add('last-modified', datetime.now())
    event['uid'] = 'ec-CSU' + student_id + 't' + datetime.now().strftime('%y%m%d%H%M%S%f') + '@admirable.one'
    event.add('rrule', {'freq' : 'weekly', 'interval': times[2],
                        'until': times[3]})
    alarm = Alarm()
    alarm.add('action', 'none')
    alarm.add('trigger', datetime(1980, 1, 1, 3, 5, 0))
    event.add_component(alarm)
    return event


if __name__ == "__main__":
    batch_generate()

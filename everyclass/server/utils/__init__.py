import os
import re

import elasticapm

from everyclass.server.config import get_config


def get_day_chinese(digit):
    """
    get Chinese char of day of week
    """
    if digit == 1:
        return '周一'
    elif digit == 2:
        return '周二'
    elif digit == 3:
        return '周三'
    elif digit == 4:
        return '周四'
    elif digit == 5:
        return '周五'
    elif digit == 6:
        return '周六'
    else:
        return '周日'


def get_time_chinese(digit):
    """
    get Chinese time description for a single lesson time.
    """
    if digit == 1:
        return '第1-2节'
    elif digit == 2:
        return '第3-4节'
    elif digit == 3:
        return '第5-6节'
    elif digit == 4:
        return '第7-8节'
    elif digit == 5:
        return '第9-10节'
    else:
        return '第11-12节'


def get_time(digit):
    """
    get start and end time for a single lesson.
    """
    if digit == 1:
        return (8, 00), (9, 40)
    elif digit == 2:
        return (10, 00), (11, 40)
    elif digit == 3:
        return (14, 00), (15, 40)
    elif digit == 4:
        return (16, 00), (17, 40)
    elif digit == 5:
        return (19, 00), (20, 40)
    else:
        return (21, 00), (22, 40)


def lesson_string_to_dict(lesson: str) -> (int, int):
    """transform str like '10102' into tuple like (1,1)"""
    day = int(lesson[0])
    time = int((int(lesson[2]) + 1) / 2)
    return day, time


def teacher_list_to_str(teachers: list):
    """parse a teacher list into a str"""
    string = ''
    for teacher in teachers:
        string = string + teacher['name'] + teacher['title'] + '、'
    return string[:len(string) - 1]


def semester_calculate(current_semester: str, semester_list: list):
    """生成一个列表，每个元素是一个二元组，分别为学期字符串和是否为当前学期的布尔值"""
    with elasticapm.capture_span('semester_calculate'):
        available_semesters = []

        for each_semester in semester_list:
            if current_semester == each_semester:
                available_semesters.append([each_semester, True])
            else:
                available_semesters.append([each_semester, False])
    return available_semesters


def teacher_list_fix(teachers: list):
    """修复老师职称“未定”，以及修复重复老师
    @:param teachers: api server 返回的教师列表
    @:return: teacher list that has been fixed
    """
    tids = []
    new_teachers = []
    for teacher in teachers:
        if teacher['title'] == '未定':
            teacher['title'] = ''

        if teacher['tid'] in tids:
            continue
        else:
            tids.append(teacher['tid'])
            new_teachers.append(teacher)
    return new_teachers


zh_pattern = re.compile(u'[\u4e00-\u9fa5]+')


def contains_chinese(word):
    """
    判断传入字符串是否包含中文
    :param word: 待判断字符串
    :return: True:包含中文  False:不包含中文
    """
    global zh_pattern
    match = zh_pattern.search(word)

    return match


def plugin_available(plugin_name: str):
    """check if a plugin (Sentry, apm, logstash) is available in the current environment."""
    config = get_config()
    return os.environ.get("MODE").lower() in getattr(config, "{}_AVAILABLE_IN".format(plugin_name).upper())

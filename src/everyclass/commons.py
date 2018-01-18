import re

from .config import load_config

config = load_config()


# 输入str"2016-2017-2"，输出[2016,2017,2]，因为参数可能来自表单提交，需要判断有效性
def tuple_semester(xq):
    if re.match(r'\d{4}-\d{4}-\d', xq):
        splited = re.split(r'-', xq)
        return int(splited[0]), int(splited[1]), int(splited[2])
    else:
        return config.DEFAULT_SEMESTER


# 因为to_string的参数一定来自程序内部，所以不检查有效性
def string_semester(xq, simplify=False):
    if not simplify:
        return str(xq[0]) + '-' + str(xq[1]) + '-' + str(xq[2])
    else:
        return str(xq[0])[2:4] + '-' + str(xq[1])[2:4] + '-' + str(xq[2])


# 判断是否为中文字符
def is_chinese(uchar):
    if u'\u4e00' <= uchar <= u'\u9fa5':
        return True
    else:
        return False


# 调试输出函数
def print_formatted_info(info, show_debug_tip=False, info_about="DEBUG"):
    from termcolor import cprint
    if show_debug_tip:
        cprint("-----" + info_about + "-----", "blue", attrs=['bold'])
    if isinstance(info, dict):
        for (k, v) in info.items():
            print("%s =" % k, v)
    elif isinstance(info, str):
        cprint(info, attrs=["bold"])
    else:
        for each_info in info:
            print(each_info)
    if show_debug_tip:
        cprint("----" + info_about + " ENDS----", "blue", attrs=['bold'])


# 获取用于数据表命名的学期，输入(2016,2017,2)，输出16_17_2
def semester_code(xq):
    if xq == '':
        return semester_code(config.DEFAULT_SEMESTER)
    else:
        if xq in config.AVAILABLE_SEMESTERS:
            return str(xq[0])[2:4] + "_" + str(xq[1])[2:4] + "_" + str(xq[2])


class NoClassException(ValueError):
    pass


class NoStudentException(ValueError):
    pass


def get_day_chinese(digit):
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
    if digit == 1:
        return [(8, 00), (9, 40)]
    elif digit == 2:
        return [(10, 00), (11, 40)]
    elif digit == 3:
        return [(14, 00), (15, 40)]
    elif digit == 4:
        return [(16, 00), (17, 40)]
    elif digit == 5:
        return [(19, 00), (20, 40)]
    else:
        return [(21, 00), (22, 40)]

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


def is_chinese_char(uchar):
    """
    Check if a char is a Chinese character. It's used to check whether a string is a name.

    :param uchar: char
    :return: True or False
    """
    if u'\u4e00' <= uchar <= u'\u9fa5':
        return True
    else:
        return False


def print_formatted_info(info, show_debug_tip=False, info_about="DEBUG"):
    """
    调试输出函数

    :param info:
    :param show_debug_tip:
    :param info_about:
    :return:
    """
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

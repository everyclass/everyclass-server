import os
import re
from typing import List, Tuple, Union

import elasticapm


def get_day_chinese(digit: int) -> str:
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


def get_time_chinese(digit: int) -> str:
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


def get_time(digit: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
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


def lesson_string_to_tuple(lesson: str) -> Tuple[int, int]:
    """transform str like '10102' into tuple like (1,1)"""
    day = int(lesson[0])
    time = int((int(lesson[2]) + 1) / 2)
    return day, time


def semester_calculate(current_semester: str, semester_list: List[str]) -> List[Tuple[str, bool]]:
    """生成一个列表，每个元素是一个二元组，分别为学期字符串和是否为当前学期的布尔值"""
    with elasticapm.capture_span('semester_calculate'):
        available_semesters = []

        for each_semester in semester_list:
            if current_semester == each_semester:
                available_semesters.append((each_semester, True))
            else:
                available_semesters.append((each_semester, False))
    return available_semesters


zh_pattern = re.compile(u'[\u4e00-\u9fa5]+')


def contains_chinese(word: str) -> bool:
    """
    判断传入字符串是否包含中文
    :param word: 待判断字符串
    :return: True:包含中文  False:不包含中文
    """
    global zh_pattern
    match = zh_pattern.search(word)

    return True if match else False


def plugin_available(plugin_name: str) -> bool:
    """
    check if a plugin (Sentry, apm, logstash) is available in the current environment.
    :return True if available else False
    """
    from everyclass.server.config import get_config
    config = get_config()
    mode = os.environ.get("MODE", None)
    if mode:
        return mode.lower() in getattr(config, "{}_AVAILABLE_IN".format(plugin_name).upper())
    else:
        raise EnvironmentError("MODE not in environment variables")


def weeks_to_string(original_weeks: List[int]) -> str:
    """
    获得周次列表的字符串表示（鉴于 API Server 转换的效果不好，暂时在本下游服务进行转换）

    :param original_weeks: int 类型的 list，每一个数字代表一个周次
    :return: 周次的字符串表示
    """

    def odd(num: int) -> bool:
        return num % 2 == 1

    def int_type_to_string(typ: int) -> str:
        if typ == 0:
            return "/周"
        elif typ == 1:
            return "/单周"
        elif typ == 2:
            return "/双周"
        else:
            raise ValueError("Unknown week type")

    processed_weeks: List[Tuple[int, int, int]] = []
    current_start = original_weeks[0]
    current_end: Union[int, None] = None
    current_type: Union[int, None] = None

    for i in range(len(original_weeks)):
        # 当前是最后一个元素
        if i == len(original_weeks) - 1:
            processed_weeks.append((current_start,
                                    current_end if current_end else current_start,
                                    current_type if current_type else 0))
            break

        # 存在下一个元素且 current_type 为空（说明当前子序列的第一个元素），则判断当前周次类型
        # 根据当前元素和下一个元素判断周次类型并保存到 current_type
        if current_type is None:
            if original_weeks[i + 1] == original_weeks[i] + 1:  # 间隔一周
                current_type = 0
            elif original_weeks[i + 1] == original_weeks[i] + 2:  # 间隔两周
                current_type = 1 if odd(current_start) else 2
            else:
                # 间隔大于两周（如：[1, 5]），拆分
                processed_weeks.append((current_start, current_start, 0))
                current_start = original_weeks[i + 1]
                current_end = None
                current_type = None
                continue

        # 有下一个元素且当前子序列已经有类型（current_type），判断下一个元素是否符合当前周类型的要求，如能则拓展子序列，不能则分割子序列
        if current_type == 0:
            if original_weeks[i + 1] == original_weeks[i] + 1:
                current_end = original_weeks[i + 1]
            else:
                # 结合具体流程可知 current_end 为 int 类型，但 flake8 把它识别为 Optional[int]，导致报错
                processed_weeks.append((current_start, current_end, current_type))  # noqa: T484
                current_start = original_weeks[i + 1]
                current_end = None
                current_type = None
        else:
            if original_weeks[i + 1] == original_weeks[i] + 2:
                current_end = original_weeks[i + 1]
            else:
                processed_weeks.append((current_start, current_end, current_type))  # noqa: T484
                current_start = original_weeks[i + 1]
                current_end = None
                current_type = None

    # 检查所有周是否都是单周、都是双周或者都是全周
    # 是则采用类似于 “1-3, 7-9/单周” 的精简表示，否则采用类似于 “1-3/单周, 4-8/双周” 的表示
    week_type: Union[int, None] = None
    week_type_consistent = True
    for week in processed_weeks:
        if week_type is None:
            week_type = week[2]
        if week[2] != week_type:
            week_type_consistent = False

    weeks_str = ""
    if week_type_consistent:
        for week in processed_weeks:
            if week[0] == week[1]:
                weeks_str += "{}, ".format(week[0])
            else:
                weeks_str += "{}-{}, ".format(week[0], week[1])
        weeks_str = weeks_str[:len(weeks_str) - 2] + int_type_to_string(processed_weeks[0][2])
    else:
        for week in processed_weeks:
            if week[0] == week[1]:
                weeks_str += "{}{}, ".format(week[0], int_type_to_string(week[2]))
            else:
                weeks_str += "{}-{}{}, ".format(week[0], week[1], int_type_to_string(week[2]))
        weeks_str = weeks_str[:len(weeks_str) - 2]

    # 如果原始表示字数更短，切换到原始表示
    plain = ", ".join([str(x) for x in original_weeks]) + int_type_to_string(0)
    if len(plain) < len(weeks_str):
        weeks_str = plain

    return weeks_str

import os
from typing import List, Tuple

from flask import current_app

from everyclass.common.env import get_env


def semester_calculate(current_semester: str, semester_list: List[str]) -> List[Tuple[str, bool]]:
    """生成一个列表，每个元素是一个二元组，分别为学期字符串和是否为当前学期的布尔值"""
    available_semesters = []

    for each_semester in semester_list:
        if current_semester == each_semester:
            available_semesters.append((each_semester, True))
        else:
            available_semesters.append((each_semester, False))
    return available_semesters


def plugin_available(plugin_name: str) -> bool:
    """
    check if a plugin (Sentry, apm, logstash) is available in the current environment.
    :return True if available else False
    """
    from everyclass.server.utils.config import get_config
    config = get_config()
    mode = os.environ.get("MODE", None)
    if mode:
        return mode.lower() in getattr(config, "{}_AVAILABLE_IN".format(plugin_name).upper())
    else:
        raise EnvironmentError("MODE not in environment variables")


def calendar_dir() -> str:
    """获得日历文件路径。生产环境为/var/calendar_files/，否则为程序根目录下的calendar_files文件夹。"""
    if get_env() == "PRODUCTION":
        return "/var/calendar_files/"
    return (current_app.root_path or "") + "/../../calendar_files/"

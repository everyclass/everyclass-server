import re
from everyclass.config import load_config

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


# 查询学生所在班级
def class_lookup(student_id):
    re_splited = re.findall(r'\d{4}', student_id)
    # 正则提取后切片切出来的班级一般是正确的，但有的学生学号并不是标准格式，因此这里对班级的前两位做一个年份判断(2010<年份<2020)
    if len(re_splited) > 1:
        re_split_result = re_splited[1]
        if 10 < int(re_split_result[0:2]) < 20:
            return re_split_result
        else:
            return "未知"
    else:
        return "未知"


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


def faculty_lookup(student_id):
    import re
    code = re.findall(r'\d{2}', student_id)[0]
    if code == '01':
        return '地球科学与信息物理学院'
    elif code == '02':
        return '资源与安全工程学院'
    elif code == '03':
        return '资源加工与生物工程学院'
    elif code == '04':  # Not sure
        return '地球科学与信息物理学院'
    elif code == '05':
        return '冶金与环境学院'
    elif code == '06':
        return '材料科学与工程学院'
    elif code == '07':
        return '粉末冶金研究院'
    elif code == '08':
        return '机电工程学院'
    elif code == '09':
        return '信息科学与工程学院'
    elif code == '10':
        return '能源科学与工程学院'
    elif code == '11':
        return '交通运输工程学院'
    elif code == '12':
        return '土木工程学院'
    elif code == '13':
        return '数学与统计学院'
    elif code == '14':
        return '物理与电子学院'
    elif code == '15':
        return '化学化工学院'
    elif code == '16':
        return '商学院'
    elif code == '17':
        return '文学与新闻传播学院'
    elif code == '18':
        return '外国语学院'
    elif code == '19':
        return '建筑与艺术学院'
    elif code == '20':
        return '法学院'
    elif code == '21':
        return '马克思主义学院'
    elif code == '22':
        return '湘雅医学院'
    elif code == '23':
        return '基础医学院'
    elif code == '24':
        return '药学院'
    elif code == '25':
        return '湘雅护理学院'
    elif code == '26':
        return '公共卫生学院'
    elif code == '27':
        return '口腔医学院'
    elif code == '28':
        return '生命科学学院'
    elif code == '37':
        return '生命科学学院'
    elif code == '39':
        return '软件学院'
    elif code == '42':
        return '航空航天学院'
    elif code == '43':
        return '公共管理学院'
    elif code == '66':
        return '体育教研部'
    elif code == '93':
        return '国际合作与交流处'
    else:
        return '未知'

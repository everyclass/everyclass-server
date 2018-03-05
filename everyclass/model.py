from flask import session

from .db_operations import get_my_semesters
from .exceptions import IllegalSemesterException


class Semester(object):
    def __init__(self, para):
        """
        构造函数，接收一个 tuple (2016,2017,2) 或者学期字符串"2016-2017-2"
        """
        # Semester("2016-2017-2")
        if isinstance(para, str):
            self.year1 = int(para[0:4])
            self.year2 = int(para[5:9])
            self.sem = int(para[10])

        # Semester((2016,2017,2))
        elif isinstance(para, tuple):
            self.year1 = int(para[0])
            self.year2 = int(para[1])
            self.sem = int(para[2])

        # illegal
        else:
            raise IllegalSemesterException

    def __repr__(self):
        return '[object Semester]: {}-{}-{}'.format(self.year1, self.year2, self.sem)

    def __str__(self):
        return '{}-{}-{}'.format(self.year1, self.year2, self.sem)

    def __eq__(self, other):
        if not isinstance(other, Semester):
            other = Semester(other)
        return self.year1 == other.year1 and self.year2 == other.year2 and self.sem == other.sem

    def to_tuple(self):
        return self.year1, self.year2, self.sem

    def to_str(self, simplify=False):
        """
        因为to_string的参数一定来自程序内部，所以不检查有效性

        :param simplify: True if you want short str
        :return: str like '16-17-2' if simplify==True, '2016-2017-2' is simplify==False
        """
        if not simplify:
            # return like '2016-2017-2'
            return str(self.year1) + '-' + str(self.year2) + '-' + str(self.sem)
        else:
            # return like '16-17-2'
            return str(self.year1)[2:4] + '-' + str(self.year2)[2:4] + '-' + str(self.sem)

    def to_db_code(self):
        """
        获取用于数据表命名的学期，如 16_17_2
        """
        return self.to_str(simplify=True).replace('-', '_')

    @staticmethod
    def get():
        """
        获取当前学期。进入此模块前必须保证 session 内有 stu_id。
        当 url 中没有显式表明 semester 时，不设置 session，而是在这里设置默认值。
        """
        from .exceptions import IllegalSemesterException

        my_available_semesters = get_my_semesters(session.get('stu_id'))[0]
        print('[model.Semester.get()] my_available_semesters:', my_available_semesters)

        # 如果 session 中包含学期信息且有效
        if session.get('semester', None) and session.get('semester', None) in my_available_semesters:
            print('[model.Semester.get()]have valid session')
            return session['semester']

        # 如果没有 session或session无效
        else:
            print('[model.Semester.get()] no session or invalid session')
            # 选择对本人有效的最后一个学期
            if my_available_semesters:
                print('[model.Semester.get()] choose last available semester')
                return my_available_semesters[-1]

            # 如果本人没有一个有效学期,则引出IllegalSemesterException
            else:
                raise IllegalSemesterException('No any available semester for this student')

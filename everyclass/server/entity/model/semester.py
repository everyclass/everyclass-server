import re


class Semester(object):
    def __init__(self, para):
        """
        构造函数，接收一个 tuple (2016,2017,2) 或者学期字符串"2016-2017-2"
        """
        # Semester("2016-2017-2")
        if isinstance(para, str) and re.match(r'\d{4}-\d{4}-\d', para):
            self.year1 = int(para[0:4])
            self.year2 = int(para[5:9])
            self.sem = int(para[10])

        # Semester("16-17-2")
        elif isinstance(para, str) and re.match(r'\d{2}-\d{2}-\d', para):
            self.year1 = int(para[0:2]) + 2000
            self.year2 = int(para[3:5]) + 2000
            self.sem = int(para[6])

        # Semester((2016,2017,2))
        elif isinstance(para, tuple):
            self.year1 = int(para[0])
            self.year2 = int(para[1])
            self.sem = int(para[2])

        # illegal
        else:
            self.year1 = 2020
            self.year2 = 2021
            self.sem = 1

    def __repr__(self):
        return '<Semester {}-{}-{}>'.format(self.year1, self.year2, self.sem)

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

import unittest
from flask import current_app
from everyclass import create_app


class TestCase1(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        # db.create_all()

    def tearDown(self):
        # db.session.remove()
        # db.drop_all()
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(current_app is None)


class BasicFunctionTestCase(unittest.TestCase):
    """basic function in everyclass/__init__.py"""

    def test_import_config(self):
        from everyclass.config import load_config
        config = load_config()
        self.assertTrue(config)

    def test_string_semester(self):
        from db.model import Semester
        self.assertTrue(Semester((2016, 2017, 2)).to_str(simplify=False) == '2016-2017-2')
        self.assertTrue(Semester((2016, 2017, 2)).to_str(simplify=True) == '16-17-2')

    def test_tuple_semester(self):
        from db.model import Semester
        self.assertTrue(Semester('2016-2017-2').to_tuple() == (2016, 2017, 2))

    def test_is_chinese_char(self):
        from everyclass.tools import is_chinese_char
        self.assertTrue(is_chinese_char('我'))
        self.assertTrue(is_chinese_char('测'))
        self.assertFalse(is_chinese_char('1'))
        self.assertFalse(is_chinese_char('A'))

    def test_get_time(self):
        from everyclass.tools import get_time
        self.assertTrue(get_time(1) == ((8, 00), (9, 40)))
        self.assertTrue(get_time(6) == ((21, 00), (22, 40)))

    def test_semester_code(self):
        from db.model import Semester
        self.assertTrue(Semester((2016, 2017, 2)).to_db_code() == "16_17_2")

    def test_get_time_chinese(self):
        from everyclass.tools import get_time_chinese
        for i in range(1, 7):
            self.assertTrue(get_time_chinese(i) == '第{}-{}节'.format(i * 2 - 1, i * 2))

    def test_get_day_chinese(self):
        from everyclass.tools import get_day_chinese
        result = [(1, '一'), (2, '二'), (3, '三'), (4, '四'), (5, '五'), (6, '六'), (7, '日')]
        for test, ans in result:
            self.assertTrue(get_day_chinese(test) == '周' + ans)

import unittest

from flask import current_app

from everyclass.server import create_app


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
        from everyclass.server.utils.config import get_config
        config = get_config()
        self.assertTrue(config)

    def test_string_semester(self):
        from everyclass.server.models import Semester
        self.assertTrue(Semester((2016, 2017, 2)).to_str(simplify=False) == '2016-2017-2')
        self.assertTrue(Semester((2016, 2017, 2)).to_str(simplify=True) == '16-17-2')

    def test_tuple_semester(self):
        from everyclass.server.models import Semester
        self.assertTrue(Semester('2016-2017-2').to_tuple() == (2016, 2017, 2))

    def test_semester_code(self):
        from everyclass.server.models import Semester
        self.assertTrue(Semester((2016, 2017, 2)).to_db_code() == "16_17_2")

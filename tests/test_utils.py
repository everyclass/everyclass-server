import unittest


class UtilTest(unittest.TestCase):
    """everyclass/server/utils"""

    def test_weeks_to_string(self):
        from everyclass.rpc.entity import weeks_to_string
        cases = (([1, 2, 3, 4, 5, 6, 7, 8], "1-8/周"),
                 ([1, 3, 5, 7], "1-7/单周"),
                 ([2, 4, 6, 8], "2-8/双周"),
                 ([1, 6], "1, 6/周"),
                 ([1, 3, 4, 6, 8], "1-3/单周, 4-8/双周"),
                 ([1], "1/周"),
                 ([1, 3, 5, 6, 7, 9, 11], "1-5/单周, 6-7/周, 9-11/单周"),
                 ([6, 7, 9, 11], "6, 7, 9, 11/周"),
                 ([1, 3, 7, 9], "1-3, 7-9/单周"),
                 ([3, 5, 6, 10], "3, 5, 6, 10/周"))
        for case in cases:
            result = weeks_to_string(case[0])
            self.assertTrue(result == case[1])

    def test_get_time_chinese(self):
        from everyclass.server.utils import get_time_chinese
        for i in range(1, 7):
            self.assertTrue(get_time_chinese(i) == '第{}-{}节'.format(i * 2 - 1, i * 2))

    def test_get_day_chinese(self):
        from everyclass.server.utils import get_day_chinese
        cases = [(1, '一'), (2, '二'), (3, '三'), (4, '四'), (5, '五'), (6, '六'), (7, '日')]
        for test, ans in cases:
            self.assertTrue(get_day_chinese(test) == '周' + ans)

    def test_get_time(self):
        from everyclass.server.utils import get_time
        cases = ((1, ((8, 00), (9, 40))),
                 (2, ((10, 00), (11, 40))),
                 (3, ((14, 00), (15, 40))),
                 (4, ((16, 00), (17, 40))),
                 (5, ((19, 00), (20, 40))),
                 (6, ((21, 00), (22, 40))),
                 )
        for time, result in cases:
            self.assertTrue(get_time(time) == result)

    def test_lesson_string_to_tuple(self):
        from everyclass.server.utils import lesson_string_to_tuple
        self.assertTrue(lesson_string_to_tuple('10102') == (1, 1))

    def test_contains_chinese(self):
        from everyclass.server.utils import contains_chinese
        self.assertTrue(contains_chinese('你好'))
        self.assertTrue(contains_chinese('你好 kitty'))
        self.assertFalse(contains_chinese('no'))


class ResourceIdentifierEncryptTest(unittest.TestCase):
    """everyclass/server/utils/resource_identifier_encrypt.py"""
    cases = (("student", "3901160407", "8ypVY3OsRhbXuGBXNpY5PEgmh53TmMfONVoRqfJ7fXY="),)
    key = "z094gikTit;5gt5h"

    def test_encrypt(self):
        from everyclass.server.utils.resource_identifier_encrypt import encrypt
        for tp, data, encrypted in self.cases:
            result = encrypt(tp, data, encryption_key=self.key)
            print("Encrypt result:", result)
            self.assertTrue(result == encrypted)

    def test_decrypt(self):
        from everyclass.server.utils.resource_identifier_encrypt import decrypt
        for tp, data, encrypted in self.cases:
            self.assertTrue(decrypt(encrypted, encryption_key=self.key, resource_type=tp) == (tp, data))

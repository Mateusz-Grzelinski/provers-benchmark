import unittest


class TestConfigFile(unittest.TestCase):

    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')
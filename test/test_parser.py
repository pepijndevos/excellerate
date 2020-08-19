import unittest
from excellerate.parser import *

class TestQ(unittest.TestCase):

    def test_literal(self):
        self.assertEqual(parse("-4e3"), -4e3)
        self.assertEqual(parse("foo"), None)

    def test_number(self):
        self.assertEqual(parse("=-4e3"), -4e3)

    def test_range(self):
        self.assertEqual(parse("=$A$4"), Range(sheet=None, boundaries=(1, 4, 1, 4)))
        self.assertEqual(parse("=A4:B5"), Range(sheet=None, boundaries=(1, 4, 2, 5)))
        self.assertEqual(parse("=sheet!A4:B5"), Range(sheet='sheet', boundaries=(1, 4, 2, 5)))
        self.assertEqual(parse("='my sheet'!A4:B5"), Range(sheet='my sheet', boundaries=(1, 4, 2, 5)))

    def test_array(self):
        self.assertEqual(parse("={1,2,3;4,5,6;7,8,9}"), Array([[1,2,3],[4,5,6],[7,8,9]]))

    def test_func(self):
        self.assertEqual(parse("=MAX(1,2,3)"), Function("MAX", [1,2,3]))

    def test_op(self):
        self.assertEqual(parse("=5>1+2*3^-4"), ('>', 5.0, ('+', 1.0, ('*', 2.0, ('^', 3.0, -4.0)))))

    def test_group(self):
        self.assertEqual(parse("=5>(1+2)*3^-4"), ('>', 5.0, ('*', ('+', 1.0, 2.0), ('^', 3.0, -4.0))))

if __name__ == '__main__':
    unittest.main() 

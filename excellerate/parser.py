from openpyxl import load_workbook
from openpyxl.utils.cell import range_to_tuple, range_boundaries
from openpyxl.formula import Tokenizer
from parsy import regex, generate, test_item, string, seq, fail
from dataclasses import dataclass
from typing import List, Tuple, Any
import unittest

def test_token(typ, subtype=None, value=None):
    def tester(token):
        return (token.type == typ and
                (subtype is None or token.subtype == subtype) and
                (value is None or token.value in value))
    return test_item(tester, f"{typ} {subtype}")

lparen = test_token("PAREN", "OPEN")
rparen = test_token("PAREN", "CLOSE")
lfunc = test_token("FUNC", "OPEN")
rfunc = test_token("FUNC", "CLOSE")
larr = test_token("ARRAY", "OPEN")
rarr = test_token("ARRAY", "CLOSE")
sep_t = test_token("SEP", "ARG")
row_t = test_token("SEP", "ROW")

lit_t = test_token("LITERAL")
number_t = test_token("OPERAND", "NUMBER")
range_t = test_token("OPERAND", "RANGE")
comp_t = test_token("OPERATOR-INFIX", value={'=', '<', '>', '<=', '>=', '<>'})
conc_t = test_token("OPERATOR-INFIX", value={'&'})
add_t = test_token("OPERATOR-INFIX", value={'+', '-'})
mult_t = test_token("OPERATOR-INFIX", value={'*', '/'})
exp_t = test_token("OPERATOR-INFIX", value={'^'})
per_t = test_token("OPERATOR-POSTFIX", value={'%'})
sign_t = test_token("OPERATOR-PREFIX", value={'+', '-'})

@dataclass
class Function:
    name: str
    args: List[Any]

@dataclass
class Array:
    elements: List[Any]

@dataclass
class Range:
    sheet: str
    boundaries: Tuple[int, int, int, int]

def make_op_parser(op, higher):
    @generate
    def op_parser():
        res = yield higher
        while True:
            operation = yield op.optional()
            if not operation:
                break
            operand = yield higher
            res = (operation.value, res, operand)
        return res
    return op_parser

def precedence(terminal, *operators):
    parser = terminal
    for op in operators:
        parser = make_op_parser(op, parser)
    return parser

@generate
def number():
    sign = yield sign_t.optional()
    value = yield number_t
    per = yield per_t.optional()
    num = float(value.value)
    if per:
        num /= 100
    return num if getattr(sign, 'value', '+') == '+' else -num


@generate
def range_():
    r = yield range_t
    if '!' in r.value:
        return Range(*range_to_tuple(r.value))
    else:
        return Range(None, range_boundaries(r.value))

@generate
def literal():
    r = yield lit_t
    try:
        return float(r.value)
    except ValueError:
        return None

@generate
def simple():
    group = lparen >> expr << rparen
    array = larr >> expr.sep_by(sep_t).sep_by(row_t).map(Array) << rarr
    func = seq(lfunc.map(lambda t: t.value[:-1]), expr.sep_by(sep_t)).combine(Function) << rfunc
    return (yield  group | array | func | number | range_)

expr = literal | precedence(simple, exp_t, mult_t, add_t, conc_t, comp_t)

def parse(formula):
    tokenizer = Tokenizer(formula)
    return expr.parse(tokenizer.items)


#### TESTS ####

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

if __name__ == '__main__':
    unittest.main() 

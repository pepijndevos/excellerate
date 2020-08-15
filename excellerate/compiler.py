from nmigen import *
from nmigen.sim.pysim import *
from openpyxl import load_workbook
from collections import defaultdict

from fixedpoint import Q
import parser

class Spreadsheet(Elaboratable):

    def __init__(self, workbook, nint=16, nfrac=16, signed=True):
        self.nint = nint
        self.nfrac = nfrac
        self.signed = signed
        self.cells = defaultdict(lambda: Q(self.nint, self.nfrac, self.signed))
        self.workbook = workbook

    def elaborate(self, platform):
        m = Module()
        for sheet in wb.sheetnames:
            for row in wb[sheet]:
                for cell in row:
                    loc = parser.Range(sheet, [cell.column, cell.row]*2)
                    ast = parser.parse(str(cell.value))
                    sig = self.compile_cell(loc, ast)
                    if sig is not None:
                        m.d.sync += self.cells[(sheet, cell.column, cell.row)].eq(sig)
        return m

    def compile_cell(self, cell, ast):
        if isinstance(ast, tuple):
            op, left, right = ast
            left = self.compile_cell(cell, left)
            right = self.compile_cell(cell, right)
            if op == '+':
                return left + right
            if op == '-':
                return left - right
            if op == '*':
                return left * right
            if op == '/':
                return left / right
            if op == '^':
                return left ** right
            if op == '>':
                return left > right
            if op == '>=':
                return left >= right
            if op == '<':
                return left < right
            if op == '<=':
                return left <= right
            if op == '=':
                return left == right
            if op == '<>':
                return left != right
        elif isinstance(ast, float):
            return Q.from_float(ast, self.nint, self.nfrac, self.signed)
        elif isinstance(ast, parser.Array):
            return Array(
                    Array(
                        Q.from_float(i, self.nint, self.nfrac, self.signed)
                        for i in row)
                    for row in ast.elements)
        elif isinstance(ast, parser.Range):
            sheet = ast.sheet or cell.sheet
            min_col, min_row, max_col, max_row = ast.boundaries
            if min_col==max_col and min_row==max_row:
                return self.cells[(sheet, min_row, min_col)]
            return Array(
                    Array(
                        self.cells[(sheet, col, row)]
                        for col in range(min_col, max_col+1))
                    for row in range(min_row, max_row+1))
        elif isinstance(ast, parser.Function):
            pass
        else:
            raise TypeError(f"{ast} is not of a supported type")

if __name__ == '__main__':
    from nmigen.cli import main
    wb = load_workbook('simple.xlsx')
    spr = Spreadsheet(wb)
    sim = Simulator(spr)
    def testbench():
        for i in range(5):
            yield Tick()
            print("###### TICK ######")
            for loc, cell in spr.cells.items():
                res = yield cell.signal
                print(loc, cell.to_float(res))

    sim.add_clock(1e-6)
    sim.add_process(testbench)
    sim.run()

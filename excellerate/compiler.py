from nmigen import *
from nmigen.sim.pysim import *
from openpyxl import load_workbook
from collections import defaultdict
from dataclasses import dataclass

from fixedpoint import Q
import parser

@dataclass(frozen=True)
class Location:
    sheet: str
    col: int
    row: int

@dataclass(frozen=True)
class Cell:
    value: Q
    ready: Signal = Signal()

class Spreadsheet(Elaboratable):

    def __init__(self, workbook, nint=16, nfrac=16, signed=True):
        self.nint = nint
        self.nfrac = nfrac
        self.signed = signed
        self.cells = defaultdict(lambda: Cell(Q(self.nint, self.nfrac, self.signed)))
        self.workbook = workbook

    def elaborate(self, platform):
        m = Module()
        for sheet in wb.sheetnames:
            for row in wb[sheet]:
                for cell in row:
                    loc = Location(sheet, cell.column, cell.row)
                    ast = parser.parse(str(cell.value))
                    sig = self.compile_cell(loc, ast)
                    if sig is not None:
                        cell = self.cells[Location(sheet, cell.column, cell.row)]
                        m.d.sync += cell.value.eq(sig.value)
                        m.d.sync += cell.ready.eq(sig.ready)
        return m

    def compile_cell(self, cell, ast):
        if not ast:
            return None
        elif isinstance(ast, tuple):
            op, left, right = ast
            lcell = self.compile_cell(cell, left)
            rcell = self.compile_cell(cell, right)
            if op == '+':
                res = lcell.value + rcell.value
            elif op == '-':
                res = lcell.value - rcell.value
            elif op == '*':
                res = lcell.value * rcell.value
            elif op == '/':
                res = lcell.value / rcell.value
            elif op == '^':
                res = lcell.value ** rcell.value
            elif op == '>':
                res = lcell.value > rcell.value
            elif op == '>=':
                res = lcell.value >= rcell.value
            elif op == '<':
                res = lcell.value < rcell.value
            elif op == '<=':
                res = lcell.value <= rcell.value
            elif op == '=':
                res = lcell.value == rcell.value
            elif op == '<>':
                res = lcell.value != rcell.value
            else:
                raise NameError(f"operator {op} not handled")
            ready = lcell.ready | rcell.ready
            return Cell(res, ready)
        elif isinstance(ast, float):
            return Cell(
                Q.from_float(ast, self.nint, self.nfrac, self.signed),
                Const(0)
            )
        elif isinstance(ast, parser.Array):
            return Cell(
                Array(
                    Array(
                        Q.from_float(i, self.nint, self.nfrac, self.signed)
                        for i in row)
                    for row in ast.elements),
                Const(0)
            )
        elif isinstance(ast, parser.Range):
            sheet = ast.sheet or cell.sheet
            min_col, min_row, max_col, max_row = ast.boundaries
            if min_col==max_col and min_row==max_row:
                return self.cells[Location(sheet, min_col, min_row)]
            return Cell(
                Array(
                    Array(
                        self.cells[Location(sheet, col, row)].value
                        for col in range(min_col, max_col+1))
                    for row in range(min_row, max_row+1)),
                Cat(self.cells[Location(sheet, col, row)]
                    for col in range(min_col, max_col+1)
                    for row in range(min_row, max_row+1)).any()
            )
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
            A1 = spr.cells[Location("Sheet1", 1, 1)].value
            yield A1.eq(A1+Q.from_float(3.0, 2, 0))
            yield Tick()
            print("###### TICK ######")
            for loc, cell in spr.cells.items():
                res = yield cell.value.signal
                print(loc, cell.value.to_float(res))

    sim.add_clock(1e-6)
    sim.add_process(testbench)
    sim.run()

from nmigen import *
from nmigen.sim.pysim import *
from dataclasses import dataclass, field

from fixedpoint import Q, QArray

@dataclass(frozen=True)
class Location:
    sheet: str
    col: int
    row: int

@dataclass(frozen=True)
class Cell:
    value: Q
    ready: Signal = field(default_factory=Signal)


class Function(Elaboratable):
    def __init__(self, *args):
        self.args = [arg.value for arg in args]
        self.self_ready = Signal(reset=1)
        self.input_ready = Cat([self.self_ready, *[arg.ready for arg in args]]).any()
        self.result = Cell(Q(self.args[0].nint, self.args[0].nfrac, self.args[0].signed))

    def flat_args(self):
        res = []
        for arg in self.args:
            if isinstance(arg, QArray):
                for arr in arg:
                    if isinstance(arr, QArray):
                        for a in arr:
                            res.append(a)
                    else:
                        res.append(arr)
            else:
                res.append(arg)
        return QArray(res)


class Sum(Function):
    def elaborate(self, platform):
        m = Module()
        args = self.flat_args()
        counter = Signal(range(len(args)))
        acc = self.result.value.like()
        with m.FSM() as fsm:
            with m.State("IDLE"):
                m.d.sync += self.result.ready.eq(0)
                m.d.sync += self.self_ready.eq(0)
                m.d.sync += counter.eq(0)
                with m.If(self.input_ready):
                    m.next = "RUNNING"
                    m.d.sync += acc.eq(Q.from_float(0, 1 ,0))
            
            with m.State("RUNNING"):
                sig = args[counter]
                m.d.sync += acc.eq(acc+sig)
                m.d.sync += counter.eq(counter+1)
                with m.If(self.input_ready): # new inputs during run
                    m.d.sync += self.self_ready.eq(1)
                    m.next = "IDLE"
                with m.If(counter >= len(args)-1):
                    m.next = "IDLE"
                    # acc is sync so need to add last result
                    m.d.sync += self.result.value.eq(acc+sig)
                    m.d.sync += self.result.ready.eq(1)

        return m

if __name__ == '__main__':
    summer = Sum(
        Cell(QArray([Q.from_float(2.0, 16, 0), Q.from_float(3.0, 16, 0)])),
        Cell(QArray([Q.from_float(5.0, 16, 0), Q.from_float(4.0, 16, 0)])),
    )
    sim = Simulator(summer)
    def testbench():
        for i in range(10):
            yield Tick()
            res = yield summer.result.value.signal
            ready = yield summer.result.ready
            print(bin(ready), res)

    sim.add_clock(1e-6)
    sim.add_process(testbench)
    with sim.write_vcd("sum.vcd"):
        sim.run()

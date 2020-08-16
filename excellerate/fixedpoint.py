from nmigen import *
from nmigen.sim.pysim import *
import math
from functools import wraps
from collections.abc import MutableSequence

import unittest
from nmigen.hdl.ast import ArrayProxy

def operator(logical=False):
    def decorator(op):
        @wraps(op)
        def do_op(*args):
            nint = max(q.nint for q in args)
            nfrac = max(q.nfrac for q in args)
            wide = [q.cast(nint, nfrac) for q in args]
            res = op(*(q.signal for q in wide))
            if logical:
                return Q(1, 0, signal=res)
            else:
                return Q(len(res)-args[0].nfrac, args[0].nfrac, signal=res)
        return do_op
    return decorator

class Q:
    def __init__(self, nint, nfrac, signed=False, signal=None, **kwargs):
        if signal is not None:
            self.signal = signal
        else:
            shape = Shape(nint+nfrac, signed)
            self.signal = Signal(shape, **kwargs)

        self.nint = nint
        self.nfrac = nfrac

    @classmethod
    def from_float(cls, value, nint, nfrac, signed=False):
        integer = int(math.floor(value*(1<<nfrac)))
        shape = Shape(nint+nfrac, signed)
        constant = Const(integer, shape)
        return Q(nint, nfrac, signal=constant)

    def to_float(self, value):
        return value/(1<<self.nfrac)

    def cast(self, nint, nfrac):
        #comment out to break abs()
        if nint==self.nint and nfrac==self.nfrac:
            return self

        start = self.nfrac-nfrac
        end = self.nfrac+nint
        sig = self.signal[max(0, start):end]
        if self.signed:
            pad_end = Repl(self.signal[-1], max(0, nint-self.nint))
        else:
            pad_end = Const(0, max(0, nint-self.nint))
        pad_start = Const(0, max(0, nfrac-self.nfrac))

        sig = Cat(pad_start, sig, pad_end)
        if self.signed:
            sig = sig.as_signed()
        return Q(nint, nfrac, signal=sig) 

    def eq(self, other):
        other = other.cast(self.nint, self.nfrac)
        return self.signal.eq(other.signal)

    def __repr__(self):
        signed = "i" if self.signed else "u"
        return f"(Q{self.nint}.{self.nfrac}{signed} {self.signal})"

    def __len__(self):
        return self.nint + self.nfrac

    def shape(self):
        return self.signal.shape()
    
    @property
    def signed(self):
        return self.signal.shape().signed

    def __bool__(self):
        raise TypeError("Attempted to convert nMigen value to Python boolean")

    @operator()
    def __invert__(self):
        return ~self
    @operator()
    def __neg__(self):
        return -self

    @operator()
    def __add__(self, other):
        return self + other
    @operator()
    def __sub__(self, other):
        return self - other

    @operator()
    def __and__(self, other):
        return self & other
    @operator()
    def __or__(self, other):
        return self | other
    @operator()
    def __xor__(self, other):
        return self ^ other

    @operator(True)
    def __gt__(self, other):
        return self > other
    @operator(True)
    def __ge__(self, other):
        return self >= other
    @operator(True)
    def __lt__(self, other):
        return self < other
    @operator(True)
    def __le__(self, other):
        return self <= other
    @operator(True)
    def __eq__(self, other):
        return self == other
    @operator(True)
    def __ne__(self, other):
        return self != other

    @operator()
    def __abs__(self):
        return abs(self)
 
    def __mul__(self, other):
        res = self.signal * other.signal
        assert len(res) == len(self)+len(other)
        return Q(self.nint+other.nint, self.nfrac+other.nfrac, signal=res)


class QArray(MutableSequence):
    def __init__(self, iterable=(), nint=None, nfrac=None, signed=None):
        if isinstance(iterable, Array) or isinstance(iterable, Value): # created from nested array
            self.signal = iterable
            self.nint = nint
            self.nfrac = nfrac
            self.signed = signed
            self.child_class = Q#self.child_attr(iterable, "__class__")
        else:
            self.signal    = Array(q.signal for q in iterable)
            self.nint = self.child_attr(iterable, "nint")
            self.nfrac = self.child_attr(iterable, "nfrac")
            self.signed = self.child_attr(iterable, "signed")
            self.child_class = self.child_attr(iterable, "__class__")

    def child_attr(self, iterable, attr):
        val = None
        for i in iterable:
            ival = getattr(i, attr)
            if val is not None:
                assert val == ival
            val = ival
        return val

    def __getitem__(self, index):
        if self.child_class == Q:
            return Q(self.nint, self.nfrac, signal=self.signal[index])
        elif self.child_class == QArray:
            return QArray(self.signal[index], self.nint, self.nfrac, self.signed)
        else:
            raise TypeError(f"{self.child_class} is not supported")

    def __len__(self):
        return len(self.signal)

    def __setitem__(self, index, value):
        self.signal[index] = value.signal

    def __delitem__(self, index):
        del self.signal[index]

    def insert(self, index, value):
        self.signal.insert(index, value.signal)

    def __repr__(self):
        return "Q" + repr(self.signal)

#### TESTS ####

def _resolve(expr):
    sim = Simulator(Module())
    a = []
    def testbench():
        a.append((yield expr))
    sim.add_process(testbench)
    sim.run()
    return a[0]

def _resolve_fp(expr):
    return expr.to_float(_resolve(expr.signal))

class TestQ(unittest.TestCase):

    def test_identity(self):
        n = Q.from_float(math.pi, 8, 16)
        m = n.cast(8, 16)
        self.assertEqual(n.signal.shape(), m.signal.shape())
        self.assertEqual(n.nint, m.nint)
        self.assertEqual(n.nfrac, m.nfrac)
        self.assertEqual(_resolve_fp(n), _resolve_fp(m))

    def test_shrink(self):
        n = Q.from_float(math.pi, 4, 4)
        m = Q.from_float(math.pi, 8, 16).cast(4, 4)
        self.assertEqual(m.signal.shape(), Shape(8, False))
        self.assertEqual(m.nint, 4)
        self.assertEqual(m.nfrac, 4)
        self.assertEqual(_resolve_fp(n), _resolve_fp(m))

    def test_grow(self):
        n = Q.from_float(math.pi, 8, 16)
        m = n.cast(16, 32)
        self.assertEqual(m.signal.shape(), Shape(48, False))
        self.assertEqual(m.nint, 16)
        self.assertEqual(m.nfrac, 32)
        self.assertEqual(_resolve_fp(n), _resolve_fp(m))

    def test_grow_signed(self):
        n = Q.from_float(-math.pi, 8, 16)
        m = n.cast(16, 32)
        self.assertEqual(m.signal.shape(), Shape(48, False))
        self.assertEqual(m.nint, 16)
        self.assertEqual(m.nfrac, 32)
        self.assertEqual(_resolve_fp(n), _resolve_fp(m))

    def test_eq(self):
        n = Q.from_float(math.pi, 8, 16)
        m = Q(4, 4)
        mod = Module()
        mod.d.comb += m.eq(n)
        sim = Simulator(mod)
        a = []
        def testbench():
            a.append((yield m.signal))
        sim.add_process(testbench)
        sim.run()
        self.assertEqual(_resolve_fp(n.cast(4, 4)), m.to_float(a[0]))

    def test_add(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(-math.pi, 8, 16, True)
        o = n+m
        self.assertEqual(o.signal.shape(), Shape(25, True))
        self.assertEqual(o.nint, 9)
        self.assertEqual(o.nfrac, 16)
        self.assertLess(abs(_resolve_fp(o)), 1e-4)

    def test_sub(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(math.pi, 8, 16, True)
        o = n-m
        self.assertEqual(o.signal.shape(), Shape(25, True))
        self.assertEqual(o.nint, 9)
        self.assertEqual(o.nfrac, 16)
        self.assertEqual(_resolve_fp(o), 0)

    def test_neg(self):
        n = -Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(-math.pi, 8, 16, True)
        self.assertEqual(n.signal.shape(), Shape(25, True))
        self.assertEqual(n.nint, 9)
        self.assertEqual(n.nfrac, 16)
        self.assertLess(_resolve_fp(n)-_resolve_fp(m), 1e-4)

    def test_inv(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = ~n
        self.assertEqual(m.signal.shape(), Shape(24, True))
        self.assertEqual(m.nint, 8)
        self.assertEqual(m.nfrac, 16)
        self.assertEqual(~_resolve(n.signal), _resolve(m.signal))

    def test_and(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(math.e, 8, 16, True)
        o = n & m
        self.assertEqual(o.signal.shape(), Shape(24, True))
        self.assertEqual(o.nint, 8)
        self.assertEqual(o.nfrac, 16)
        self.assertEqual(_resolve(o.signal), _resolve(m.signal)&_resolve(n.signal))

    def test_or(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(math.e, 8, 16, True)
        o = n | m
        self.assertEqual(o.signal.shape(), Shape(24, True))
        self.assertEqual(o.nint, 8)
        self.assertEqual(o.nfrac, 16)
        self.assertEqual(_resolve(o.signal), _resolve(m.signal)|_resolve(n.signal))

    def test_xor(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(math.e, 8, 16, True)
        o = n ^ m
        self.assertEqual(o.signal.shape(), Shape(24, True))
        self.assertEqual(o.nint, 8)
        self.assertEqual(o.nfrac, 16)
        self.assertEqual(_resolve(o.signal), _resolve(m.signal)^_resolve(n.signal))

    def test_gt(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(math.e, 8, 16, True)
        o = n > m
        self.assertEqual(o.signal.shape(), Shape(1, False))
        self.assertEqual(o.nint, 1)
        self.assertEqual(o.nfrac, 0)
        self.assertEqual(_resolve(o.signal), 1)

    def test_ge(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(math.e, 8, 16, True)
        o = n >= m
        self.assertEqual(o.signal.shape(), Shape(1, False))
        self.assertEqual(o.nint, 1)
        self.assertEqual(o.nfrac, 0)
        self.assertEqual(_resolve(o.signal), 1)

    def test_lt(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(math.e, 8, 16, True)
        o = n < m
        self.assertEqual(o.signal.shape(), Shape(1, False))
        self.assertEqual(o.nint, 1)
        self.assertEqual(o.nfrac, 0)
        self.assertEqual(_resolve(o.signal), 0)

    def test_lt(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(math.e, 8, 16, True)
        o = n <= m
        self.assertEqual(o.signal.shape(), Shape(1, False))
        self.assertEqual(o.nint, 1)
        self.assertEqual(o.nfrac, 0)
        self.assertEqual(_resolve(o.signal), 0)

    def test_repr(self):
        n = Q.from_float(math.pi, 8, 16, True)
        self.assertEqual(repr(n), "(Q8.16i (const 24'sd205887))")

    def test_abs(self):
        n = Q.from_float(-math.pi, 8, 16, True)
        m = abs(n)
        self.assertEqual(bin(_resolve(m.signal)), bin(_resolve(-n.signal)))

    def test_mul(self):
        n = Q.from_float(math.pi, 8, 16, True)
        m = Q.from_float(2.0, 2, 1, False)
        o = n*m
        self.assertEqual(o.signal.shape(), Shape(27, True))
        self.assertEqual(o.nint, 10)
        self.assertEqual(o.nfrac, 17)
        self.assertLess(abs(_resolve_fp(o)-2*math.pi), 1e-4)

class TestQArray(unittest.TestCase):

    def test_lookup(self):
        a = QArray([
            Q.from_float(math.pi, 8, 16),
            Q.from_float(math.e, 8, 16),
            Q.from_float(1, 8, 16),
            ])
        n = a[0]
        m = a[Const(0)]
        self.assertEqual(type(m), Q)
        self.assertEqual(type(m.signal), ArrayProxy)
        self.assertEqual(m.nint, 8)
        self.assertEqual(m.nfrac, 16)
        self.assertEqual(m.signed, False)
        self.assertEqual(_resolve_fp(n), _resolve_fp(m))

    def test_nested_lookup(self):
        a = QArray([
                QArray([
                    Q.from_float(math.pi, 8, 16),
                    Q.from_float(math.e, 8, 16),
                    Q.from_float(1, 8, 16),
                    ]),
                QArray([
                    Q.from_float(math.pi, 8, 16),
                    Q.from_float(math.e, 8, 16),
                    Q.from_float(1, 8, 16),
                    ])
            ])
        n = a[0][0]
        m = a[Const(0)][Const(0)]
        self.assertEqual(type(m), Q)
        self.assertEqual(type(m.signal), ArrayProxy)
        self.assertEqual(m.nint, 8)
        self.assertEqual(m.nfrac, 16)
        self.assertEqual(m.signed, False)
        self.assertEqual(_resolve_fp(n), _resolve_fp(m))

if __name__ == '__main__':
    unittest.main() 

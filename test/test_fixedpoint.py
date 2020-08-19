from excellerate.fixedpoint import *
import unittest
from nmigen.hdl.ast import ArrayProxy

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
            Q.from_float(math.e, 16, 16),
            Q.from_float(1, 8, 16),
            ])
        n = a[0]
        m = a[Const(0)]
        self.assertEqual(type(m), Q)
        self.assertEqual(type(m.signal), ArrayProxy)
        self.assertEqual(m.nint, 16)
        self.assertEqual(m.nfrac, 16)
        self.assertEqual(m.signed, False)
        self.assertLess(abs(_resolve_fp(n)-math.pi), 1e-4)
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
                    Q.from_float(math.e, 16, 16),
                    Q.from_float(1, 8, 16),
                    ])
            ])
        n = a[0][0]
        m = a[Const(0)][Const(0)]
        self.assertEqual(type(m), Q)
        self.assertEqual(type(m.signal), ArrayProxy)
        self.assertEqual(m.nint, 16)
        self.assertEqual(m.nfrac, 16)
        self.assertEqual(m.signed, False)
        self.assertLess(abs(_resolve_fp(n)-math.pi), 1e-4)
        self.assertEqual(_resolve_fp(n), _resolve_fp(m))

if __name__ == '__main__':
    unittest.main() 

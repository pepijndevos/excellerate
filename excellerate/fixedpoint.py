from nmigen import *
from nmigen.sim.pysim import *
import math
from functools import wraps
from collections.abc import MutableSequence

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
                return Q(len(res)-nfrac, nfrac, signal=res)
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

    def like(self):
        return Q(self.nint, self.nfrac, self.signed)

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
            self.child_class = Q # assume 2 levels of nesting
        else:
            self.nint = max(q.nint for q in iterable)
            self.nfrac = max(q.nfrac for q in iterable)
            self.signed = max(q.nfrac for q in iterable)
            self.child_class = self.child_attr(iterable, "__class__")
            if self.child_class == Q:
                self.signal = Array(q.cast(self.nint, self.nfrac).signal for q in iterable)
            elif self.child_class == QArray:
                self.signal = Array(q.signal for q in iterable)

    def child_attr(self, iterable, attr):
        val = None # empty array will return None
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


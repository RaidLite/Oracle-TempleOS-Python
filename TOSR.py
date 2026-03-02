import os
import time
import math
import random
import socket
import struct
import hashlib
import threading
import gc
import platform

def _chaos_hash(data: bytes) -> int:
    h = hashlib.sha3_512(data).digest()
    h = hashlib.blake2b(h).digest()
    h = hashlib.sha512(h).digest()
    return int.from_bytes(h, "big")

def _memory_noise():
    objs = gc.get_objects()
    s = 0
    step = max(1, len(objs) // 128 or 1)
    for i in range(0, len(objs), step):
        s ^= id(objs[i])
    return s

def _timing_jitter():
    t1 = time.perf_counter_ns()
    for _ in range(random.randint(10, 200)):
        math.sqrt(random.random())
    t2 = time.perf_counter_ns()
    return t2 - t1


def _collect_noise():
    e = bytearray()
    e += os.urandom(64)
    e += struct.pack("Q", time.time_ns())
    e += struct.pack("Q", _memory_noise())
    e += struct.pack("Q", _timing_jitter())
    e += struct.pack("d", math.sin(time.perf_counter()))
    e += struct.pack("d", math.cos(random.random()))
    e += random.getrandbits(128).to_bytes(16, "big")
    return _chaos_hash(e)


def _bootstrap():
    e = bytearray()
    e += os.urandom(128)
    e += struct.pack("Q", time.time_ns())
    e += struct.pack("d", time.perf_counter())
    e += struct.pack("Q", os.getpid())
    e += socket.gethostname().encode()
    e += platform.platform().encode()
    e += struct.pack("Q", _memory_noise())
    e += struct.pack("Q", _timing_jitter())
    e += random.getrandbits(256).to_bytes(32, "big")
    return _chaos_hash(e)


class MadNoiseRNG:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = _bootstrap()

    def _step(self):
        with self._lock:
            a = 6364136223846793005
            c = 1442695040888963407
            m = 2**64
            self._state = (a * self._state + c) % m
            self._state ^= _collect_noise()
            self._state &= (1 << 64) - 1
            return self._state

    def randbits(self, bits: int):
        if bits <= 0:
            return 0
        result = 0
        generated = 0
        while generated < bits:
            result <<= 64
            result |= self._step()
            generated += 64
        return result & ((1 << bits) - 1)

    def randbelow(self, n: int):
        if n <= 0:
            return 0
        bits = n.bit_length()
        while True:
            r = self.randbits(bits)
            if r < n:
                return r

    def choice(self, seq):
        if not seq:
            raise IndexError("empty sequence")
        return seq[self.randbelow(len(seq))]

_rng = MadNoiseRNG()

def mad_choice(seq):
    return _rng.choice(seq)
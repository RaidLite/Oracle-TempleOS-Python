import sys
import threading
import time

from TOSR import mad_choice

class Future:
    def __init__(self):
        self.done = False
        self.value = None
        self.waiters = []

    def set(self, value=None):
        if self.done:
            return
        self.done = True
        self.value = value
        for w in self.waiters:
            w(self)

    def add(self, fn):
        if self.done:
            fn(self)
        else:
            self.waiters.append(fn)

    def __await__(self):
        yield self
        return self.value


class Task:
    def __init__(self, coro, loop):
        self.coro = coro
        self.loop = loop
        self._step(None)

    def _step(self, value):
        try:
            fut = self.coro.send(value)
            fut.add(self._wakeup)
        except StopIteration:
            pass

    def _wakeup(self, fut):
        self.loop.call(self._step, fut.value)


class Loop:
    def __init__(self):
        self.ready = []

    def call(self, fn, *args):
        self.ready.append((fn, args))

    def task(self, coro):
        Task(coro, self)

    def tick(self):
        if self.ready:
            fn, args = self.ready.pop(0)
            fn(*args)
        else:
            time.sleep(0.01)


def sleep(loop, delay):
    f = Future()

    def timer():
        time.sleep(delay)
        loop.call(f.set)

    threading.Thread(target=timer, daemon=True).start()
    return f


async def typewriter(loop, text, delay):
    in_word = False
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()

        if ch.isalnum():
            if not in_word:
                in_word = True
        else:
            in_word = False

        await sleep(loop, delay)


def _read_words(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        return ["FAITH", "LOGIC", "VOID", "APPLE", "GATE", "HEAVEN"]


def _format_text(text):
    words = []
    for w in text.split():
        words.append(w.capitalize())

    lines = []
    cur = []
    ln = 0

    for w in words:
        if ln + len(w) + 1 > 60:
            lines.append(' '.join(cur))
            cur = [w]
            ln = len(w)
        else:
            cur.append(w)
            ln += len(w) + 1

    if cur:
        lines.append(' '.join(cur))

    return '\n'.join(lines)


class God:
    def __init__(self, path, amount):
        self.words = _read_words(path)
        self.amount = amount

    def speak(self):
        raw = ' '.join(mad_choice(self.words) for _ in range(self.amount))
        return _format_text(raw)


def main():
    loop = Loop()
    text = "God says.... " + God("HAPPY.TXT", 32).speak()

    loop.task(typewriter(loop, text, 0.05))

    try:
        while True:
            loop.tick()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
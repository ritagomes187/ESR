import sys, threading
sys.path.append("../")


class Queue:
    def __init__(self):
        self._queue = []

    def put(self, x):
        self._queue.append(x)

    def take(self):
        try:
            return self._queue.pop(0)
        except:
            return

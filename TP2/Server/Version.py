import sys, socket, threading
sys.path.append('../')

class Version:
    def __init__(self):
        self._vs = 0

    def inc(self):
        self._vs += 1
        return self._vs

    @property
    def vs(self):
        return self._vs
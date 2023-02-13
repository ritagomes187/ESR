import sys, threading
sys.path.append("../")

from RTP.RTPPacket import RTPPacket

class Queue:
  def __init__(self):
    self._lock = threading.RLock()
    self._cond = threading.Condition(self._lock)
    self._queue = []
    self._forceStop = False
  
  def get(self):
    with self._lock:
      while not self._forceStop and not self._queue:
        self._cond.wait()
      if self._queue:
        x, *self._queue = self._queue
        return x
  
  def put(self, x):
    with self._lock:
      self._queue.append(x)
      self._cond.notify_all()

  def forceStop(self):
    with self._lock:
      self._forceStop = True
      self._cond.notify_all()

class VideoBufferListener:
  def __init__(self, ip : str):
    self.ip = ip
    self._buffer = Queue()

  def put(self, pkt : RTPPacket) -> None:
    self._buffer.put(pkt)

  def get(self) -> RTPPacket:
    return self._buffer.get()

  def forceStop(self):
    self._buffer.forceStop()

class VideoBufferObserver:
  def __init__(self):
    self._lock = threading.RLock()
    self._listeners : dict[str, VideoBufferListener] = {}

  def addListener(self, vbl : VideoBufferListener) -> None:
    with self._lock:
      self._listeners[vbl.ip] = vbl
  
  def rmListener(self, ip : str) -> VideoBufferListener:
    with self._lock:
      self._listeners.pop(ip, None)
      return bool(self._listeners)
  
  def put(self, pkt : RTPPacket) -> bool:
    with self._lock:
      for l in self._listeners.values():
        l.put(pkt)
    return not pkt.more

  def forceStop(self):
    with self._lock:
      for l in self._listeners.values():
        l.forceStop()
      self._listeners = {}

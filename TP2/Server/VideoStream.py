import sys, threading, time
sys.path.append("../")

from RTP.RTPPacket import RTPPacket
from Misc.RouteTable import RouteTable

class VideoStream:
  def __init__(self, vbo, routeTable):
    self._vbo : VideoBufferObserver = vbo
    self._routeTable : RouteTable   = routeTable
    self._process : bool            = False
    self._lock : threading.Rlock    = threading.RLock()

  def _nextFrame(self):
    data = self._file.read(5)
    if data:
      l = int(data)
      data = self._file.read(l)
      return RTPPacket(True, data)
    else:
      return RTPPacket(False, b"")

  def activate(self, filename):
    with self._lock:
      if not self._process:
        self._process = True
        threading.Thread(target=self._start, args=(filename,)).start()

  def addListener(self, ip):
    self._vbo.addListener(ip)

  def rmListener(self, ip):
    if not self._vbo.rmListener(ip):
      self._process = False

  def _start(self, filename):
    try:
      with open(filename, "rb") as self._file:
        while True:
          with self._lock:
            if not self._process:
              break
          pkt = self._nextFrame()
          self._vbo.put(pkt)
          if not pkt.more:
            break
          time.sleep(0.05)
    except:
      raise IOError
    finally:
      with self._lock:
        self._process = False
      self._vbo.forceStop()
      self._routeTable.stopReceiving()

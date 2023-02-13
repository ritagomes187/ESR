import socket, sys, threading,time
sys.path.append("../")

from RTP.VideoBuffer import VideoBufferListener, VideoBufferObserver
from RTP.RTPPacket import RTPPacket
from Misc.RouteTable import RouteTable

BUFFER_SIZE = RTPPacket.get_max_size()

class RTPReceiver:
  def __init__(self, vbo, routeTable):
    self._vbo : VideoBufferObserver = vbo
    self._routeTable : RouteTable   = routeTable
    self._process : bool            = False
    self._lock : threading.RLock    = threading.RLock()

  def activate(self, addr):
    with self._lock:
      if not self._process:
        self._process = True
        threading.Thread(target=self._start,args=(addr,)).start()

  def addListener(self, ip):
    with self._lock:
      self._vbo.addListener(ip)

  def rmListener(self, ip):
    with self._lock:
      if not self._vbo.rmListener(ip):
        self._vbo.forceStop()
        self._process = False

  def _start(self, addr):
    try:
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(addr)
        s.listen()
        conn, addr = s.accept()
        print("receiver conectou-se")
        while True:
          with self._lock:
            if not self._process:
              break
          msg = conn.recv(BUFFER_SIZE)
          pkt = RTPPacket.decode(msg)
          self._vbo.put(pkt)
          if not pkt.more:
            break
    except:
      pass
    finally:
      print("fim receiver")
      with self._lock:
        self._process = False
      self._vbo.forceStop()
      self._routeTable.stopReceiving()

class RTPSender:
  def __init__(self, addr, vbl, routeTable):
    self._addr : tuple[str,int]     = addr
    self._vbl : VideoBufferListener = vbl
    self._routeTable : RouteTable   = routeTable

  def start(self):
    try:
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(self._addr)
        print("sender conectou-se")
        while True:
          pkt = self._vbl.get()
          if pkt:
            s.sendall(pkt.encode())
            if not pkt.more:
              break
          else:
            break
    except:
      pass
    finally:
      print("fim sender")
      self._routeTable.deactivateRoute(self._addr[0])

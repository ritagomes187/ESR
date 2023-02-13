import sys, socket, time, threading
sys.path.append('../')

from Misc.Util import DATA_PORT
from InfoPacket.InfoPacket import InfoPacket
from InfoPacket.DelayPacket import DelayPacket
from InfoPacket.MetricPacket import MetricPacket
from InfoPacket.Tag import Tag
from InfoPacket.InvalidTag import InvalidTag
from RTP.RTPWorker import RTPSender, RTPReceiver
from RTP.VideoBuffer import VideoBufferObserver, VideoBufferListener
from Misc.RouteTable import RouteTable

TIMEOUT_BEACON = 5
BUFFER_SIZE    = 256
INTERVAL_TIME  = 1

class NodeWorker:  
  def __init__(self, 
      addr, 
      routeTable,
      ngh,
      rtpr,
      queue,
      socket = None):
    self._addr = addr
    self._routeTable = routeTable
    self._ngh = ngh
    self._rtpr = rtpr
    self._vbl = None
    self._socket = socket
    self._queue = queue

  # @timeout_decorator.timeout(TIMEOUT_BEACON)
  def receive(self):
    msg = self._socket.recv(BUFFER_SIZE)
    return InfoPacket.decode(msg)

  def processHI(self, payload):
    self._ngh.addDest(self._addr[0])
    if self._routeTable:
      for rt in self._routeTable.values():
        if self._addr[0] not in rt._dests:
          rt.addDest(self._addr[0])


  def processALIVE(self, payload):
    pass

  def processMETRIC(self, payload):
    pk = MetricPacket.fromInfoPacket(payload.decode())
    src = pk.src
    nh = int(pk.metric)
    if self._routeTable and self._routeTable.get(src,None):
      if self._addr[0] not in self._routeTable[src]._dests:
        rt.addDest(self._addr[0])
      newBest = self._routeTable[src].addEntry(self._addr[0],nh)
    else:
      rt = RouteTable(src)
      map(rt.addDest, self._ngh.dests)
      rt.addEntry(self._addr[0],nh)
      self._routeTable[src] = rt

  def processPLAY(self, payload):
    src = payload.decode()
    if not self._vbl:
      self._vbl = VideoBufferListener(self._addr[0])
      self._rtpr.addListener(self._vbl)

      self._routeTable[src].activateRoute(self._addr[0])
      self._rtpr.activate(("", DATA_PORT))

      rtps = RTPSender((self._addr[0], DATA_PORT), self._vbl, self._routeTable[src])
      threading.Thread(target=rtps.start).start()

  def processSTOP(self, payload):
    src = payload.decode()
    if self._vbl:
      self._vbl.forceStop()
      self._vbl = None
      self._rtpr.rmListener(self._addr[0])
      self._routeTable[src].deactivateRoute(self._addr[0])

  def processDELAY(self, payload):
    for k,v in self._queue.items():
      if k != self._addr[0]:
        v.put(payload)

  def default(self, payload):
    pass

  def start(self):
    try:
      if self._socket is None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(self._addr)

      with self._socket:
        
        if self._routeTable:
          for src, rt in self._routeTable.items():
            rt.firstMessage(self._addr[0],src)
        
        while True:
          
          if self._routeTable:
            
            for rt in self._routeTable.values():
              msg = rt.popMsg(self._addr[0])
              infp = msg if msg else InfoPacket(Tag.ALIVE)
              self._socket.sendall(infp.encode())
          else:
            self._socket.sendall(InfoPacket(Tag.HI).encode())

          while (p := self._queue[self._addr[0]].take()) is not None:
            self._socket.sendall(InfoPacket(Tag.DELAY, p).encode())
          try:
            infp = self.receive()
            print(self._addr, infp)
            {
              Tag.HI:     self.processHI,
              Tag.ALIVE:  self.processALIVE,
              Tag.METRIC: self.processMETRIC,
              Tag.PLAY:   self.processPLAY,
              Tag.STOP:   self.processSTOP,
              Tag.DELAY:  self.processDELAY
            }.get(infp.tag, self.default)(infp.payload)
          except InvalidTag:
            pass
          time.sleep(INTERVAL_TIME)
    except:
      self._rtpr.rmListener(self._addr[0])
      if self._vbl:
        self._vbl.forceStop()
        self._vbl = None
      for src in self._routeTable.keys():
        self._routeTable[src].remove(self._addr[0])

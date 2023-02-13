import sys, socket, time, threading,datetime
sys.path.append('../')

from Misc.Util import DATA_PORT
from VideoStream import VideoStream
from InfoPacket.InfoPacket import InfoPacket,BUFFER_SIZE
from InfoPacket.DelayPacket import DelayPacket
from InfoPacket.Tag import Tag
from InfoPacket.InvalidTag import InvalidTag
from RTP.RTPWorker import RTPSender
from RTP.VideoBuffer import VideoBufferObserver, VideoBufferListener


TIMEOUT_BEACON = 5

INTERVAL_TIME  = 1
INTERVAL_DELAY =10

FILENAME = "movie.Mjpeg"

class ServerWorker:  
  def __init__(self,
      ip,
      addr, 
      routeTable,
      videoStream,
      socket,
      queue):
    self._ip = ip
    self._addr = addr
    self._routeTable = routeTable
    self._videoStream = videoStream
    self._vbl = None
    self._socket = socket
    self._queue = queue

  # @timeout_decorator.timeout(TIMEOUT_BEACON)
  def receive(self):
    msg = self._socket.recv(BUFFER_SIZE)
    return InfoPacket.decode(msg)

  def processHI(self, payload):
    self._routeTable.addDest(self._addr[0])

  def processALIVE(self, payload):
    pass

  def processMETRIC(self, payload):
    pass

  def processPLAY(self, payload):
    if not self._vbl:
      self._vbl = VideoBufferListener(self._addr[0])
      self._videoStream.addListener(self._vbl)
      
      self._routeTable.activateRoute(self._addr[0])
      self._videoStream.activate(FILENAME)

      rtps = RTPSender((self._addr[0], DATA_PORT), self._vbl, self._routeTable)
      threading.Thread(target=rtps.start).start()

  def processSTOP(self, payload):
    if self._vbl:
      self._vbl.forceStop()
      self._vbl = None
      self._videoStream.rmListener(self._addr[0])
      self._routeTable.deactivateRoute(self._addr[0])

  def processDELAY(self,payload):
    pass

  def sendDELAY(self,vs):
    timestamp = datetime.datetime.now().timestamp()
    pk = DelayPacket(vs, self._ip , timestamp).toInfoPacket()
    self._socket.sendall(pk.encode())

  def default(self, payload):
    pass

  def start(self):
    try:
      with self._socket:
        self._routeTable.firstMessage(self._addr[0],self._ip)
        while True:
          msg = self._routeTable.popMsg(self._addr[0])
          infp = msg if msg else InfoPacket(Tag.ALIVE)
          self._socket.sendall(infp.encode())
          while q := self._queue.take():
            self.sendDELAY(q[0])
            
          try:
            infp = self.receive()
            print(self._addr, infp)
            {
              Tag.HI:     self.processHI,
              Tag.ALIVE:  self.processALIVE,
              Tag.PLAY:   self.processPLAY,
              Tag.STOP:   self.processSTOP,
              Tag.DELAY:  self.processDELAY
            }.get(infp.tag, self.default)(infp.payload)
          except InvalidTag:
            pass

          time.sleep(INTERVAL_TIME)
    except:
      self._videoStream.rmListener(self._addr[0])
      if self._vbl:
        self._vbl.forceStop()
      self._routeTable.remove(self._addr[0])

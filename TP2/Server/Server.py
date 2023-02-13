import sys, socket, threading,datetime, time
sys.path.append('../')

from Misc.Util import INFO_PORT
from ServerWorker import ServerWorker
from VideoStream import VideoStream
from Misc.RouteTable import RouteTable
from RTP.VideoBuffer import VideoBufferObserver, VideoBufferListener
from RTP.RTPWorker import RTPSender
from Version import Version
from Node.Queue import Queue


def name(vs : Version, queues : dict):
  while True:
    for v in queues.values():
      v.put([vs.vs,"Send"])
    vs.inc()
    time.sleep(30)

class Server:
  def __init__(self,ip):
    self._ip = ip
    self._routeTable = RouteTable()
    self._routeTable.addEntry("S", 0)
    self._videoStream = VideoStream(VideoBufferObserver(), self._routeTable)
    self._version = Version()
    self._queue = {} 

  def acceptConnections(self):
    try:
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", INFO_PORT))
        s.listen()
        threading.Thread(target = name, args=(self._version, self._queue)).start()
        while True:
          conn, addr = s.accept()
          self._queue[addr[0]] = Queue()
          sw = ServerWorker(self._ip, (addr[0],INFO_PORT), self._routeTable, self._videoStream, conn, self._queue[addr[0]])
          thread = threading.Thread(target=sw.start)
          thread.start()
    except:
      pass

  def start(self):
    self.acceptConnections()

Server(sys.argv[1]).start()



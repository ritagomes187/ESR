import sys, socket, threading
sys.path.append('../')

from NodeWorker import NodeWorker
from Misc.RouteTable import RouteTable
from Misc.Util import INFO_PORT
from RTP.VideoBuffer import VideoBufferObserver, VideoBufferListener
from RTP.RTPWorker import RTPReceiver, RTPSender
from Neighbors import Neighbors
from Queue import Queue

class Node:
  def __init__(self, args):
    self._ip         = ''
    self._neighbors  = set(args)
    self._ngh        = Neighbors() 
    self._routeTable : dict[str,RouteTable] = {}
    self._rtpr       = RTPReceiver(VideoBufferObserver(), self._routeTable)
    self._queue = {}

  def createConnections(self):
    for neighbor in self._neighbors:
      self._ngh.addDest(neighbor) 
      self._queue[neighbor] = Queue()
      nw = NodeWorker((neighbor,INFO_PORT), self._routeTable, self._ngh, self._rtpr, self._queue)
      threading.Thread(target=nw.start).start()

  def acceptConnections(self):
    try:
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((self._ip, INFO_PORT))
        s.listen()
        while True:
          conn, addr = s.accept()
          self._queue[addr[0]] = Queue()
          bw = NodeWorker((addr[0],INFO_PORT), self._routeTable, self._ngh, self._rtpr, self._queue,conn)
          threading.Thread(target=bw.start).start()
    except:
      pass

  def start(self):
    """Main function
    """
    self.createConnections()
    threading.Thread(target=self.acceptConnections).start()

try:
 # IP = sys.argv[1]
  NEIGHBORS = sys.argv[1:]
  Node(NEIGHBORS).start()
except:
  print("Usage: Node.py [Neighbor1_ip Neighbor2_ip ...]\n")
import sys, socket, threading
sys.path.append('../')

from NodeWorker import NodeWorker
from Misc.RouteTable import RouteTable
from InfoPacket.InfoPacket import InfoPacket
from Misc.Util import INFO_PORT
from RTP.VideoBuffer import VideoBufferObserver, VideoBufferListener
from RTP.RTPWorker import RTPReceiver, RTPSender
from Queue import Queue

class Neighbors:
    def __init__(self):
        self._dests : list[str] = []

    @property
    def dests(self):
        return self._dests

    def addDest(self, dest: str) -> None:
        self._dests.append(dest)
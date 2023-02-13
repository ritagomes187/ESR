import sys, datetime
sys.path.append('../')
from InfoPacket.InfoPacket import InfoPacket
from InfoPacket.InfoPacket import BUFFER_SIZE
from InfoPacket.Tag import Tag

SEPARATOR = '-'

class DelayPacket:
  def __init__(self, vs: int, src: str, timestamp: datetime) -> None:
    self._vs = vs
    self._src = src
    self._timestamp = timestamp

  @property
  def vs(self):
    return self._vs

  @property
  def src(self):
    return self._src

  @property
  def timestamp(self):
    return self._timestamp

  @property
  def payload(self):
    return f'{self.vs}{SEPARATOR}{self.src}{SEPARATOR}{self.timestamp}'.encode()

  def toInfoPacket(self) -> InfoPacket:
    return InfoPacket(Tag.DELAY, self.payload)

  @staticmethod
  def fromInfoPacket(infpac: InfoPacket):
    if infpac.tag == Tag.DELAY:
      vs, src, timestamp = infpac._payload.decode().split(SEPARATOR) 
      return DelayPacket(vs,src,float(timestamp))
import sys
sys.path.append('../')
from InfoPacket.Tag import Tag
from InfoPacket.InvalidTag import InvalidTag

BUFFER_SIZE    = 256

class InfoPacket:
  def __init__(self, tag, payload = b""):
    self._tag     = tag
    self._payload = payload

  def __str__(self):
    return f"Tag: {self._tag.name}, Message: {(self._payload)}"

  @property
  def tag(self):
    return self._tag

  @property
  def payload(self):
    return self._payload
  
  def encode(self):
    l = self._tag.msg + \
        self._payload
    return l + b' '*(BUFFER_SIZE - len(l))

  @staticmethod
  def decode(message):
    try:
      tag = Tag(int(message[:Tag.size()]))
      payload = message[Tag.size():].strip()

      return InfoPacket(tag, payload)
    except:
      raise InvalidTag(str(message[:Tag.size()]))

  @staticmethod
  def mkPSPacket(tag,src):
    return InfoPacket(tag,str(src).encode("utf8"))

  #@staticmethod
  #def mkMetricPacket(metric):
  #  return InfoPacket(Tag.METRIC,str(metric).encode("utf8"))
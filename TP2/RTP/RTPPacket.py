class RTPPacket:
  def __init__(self, more, payload):
    self._more = more
    self._payload = payload
  
  @property
  def payload(self):
    return self._payload

  @property
  def more(self):
    return self._more  

  @staticmethod
  def get_max_payload_size():
    return PAYLOAD_SIZE

  @staticmethod
  def get_max_size():
    return 20480

  def _enc_more(self):
    return str(int(self._more)).encode("utf8")

  #pacote para byte
  def encode(self):
    return self._enc_more() + self._payload

  #bytes para pacote
  @staticmethod
  def decode(byteStream):
    more = bool(int(byteStream[0]))
    payload = byteStream[1:]
    return RTPPacket(more,payload)

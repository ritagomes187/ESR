from enum import IntEnum, unique

@unique
class Tag(IntEnum):
  HI     = 1
  ALIVE  = 2
  METRIC = 3
  PLAY   = 4
  STOP   = 5
  DELAY  = 6

  @staticmethod
  def size():
    return 1

  @property
  def msg(self):
    b = str(self.value).encode("utf8")
    b = (Tag.size() - len(b)) * b"0" + b
    return b
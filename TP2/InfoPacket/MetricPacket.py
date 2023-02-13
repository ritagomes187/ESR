import sys, datetime
sys.path.append('../')
from InfoPacket.InfoPacket import InfoPacket
from InfoPacket.InfoPacket import BUFFER_SIZE
from InfoPacket.Tag import Tag

SEPARATOR = '-'

class MetricPacket:
    def __init__(self, src, metric) -> None:
        self._src = src
        self._metric = metric

    @property
    def src(self):
        return self._src
    
    @property
    def metric(self):
        return self._metric

    @property
    def payload(self):
        return f'{self.src}{SEPARATOR}{self.metric}'.encode()

    def mkMetricPacket(self):
        return InfoPacket(Tag.METRIC,self.payload)

    @staticmethod
    def fromInfoPacket(infpac: str):
        src, metric = infpac.split(SEPARATOR)
        return MetricPacket(src,metric)
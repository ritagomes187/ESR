import threading
import sys
sys.path.append('../')

from InfoPacket.InfoPacket import InfoPacket
from InfoPacket.MetricPacket import MetricPacket
from InfoPacket.Tag import Tag
from RTP.VideoBuffer import VideoBufferObserver

class RouteTable:
  def __init__(self,server = ""):
    self._lockChosen                    = threading.RLock()
    self._receiving : tuple[bool, bool] = (False, False) # Actual / To be warned
    self._chosen : tuple[str, int]      = None

    self._lockSubs              = threading.RLock()
    self._subs : dict[str, int] = {}

    self._lockDests                                  = threading.RLock()
    self._dests : dict[str, tuple[InfoPacket, bool]] = {}
    self._server = server

  def popMsg(self, ip : str) -> InfoPacket:
    # Se for o  escolhido
    with self._lockChosen:
      if self._chosen and ip == self._chosen[0]:
        actual, toBeWarned = self._receiving
        if toBeWarned:
          try:
            return (InfoPacket.mkPSPacket(Tag.PLAY,self._server) \
              if actual \
              else InfoPacket.mkPSPacket(Tag.STOP,self._server))
          finally:
            self._receiving =  (actual, False)
        else:
          return
    # Se não for o escolhido
    with self._lockDests:
      d = self._dests.get(ip,None)
      if d is None:
        res = None
      else:
        res = d[0]
        self._dests[ip] = (None, d[1])
      return res

  def firstMessage(self, ip : str, src):
    with self._lockDests:
      with self._lockChosen:
        pkt = MetricPacket(src,self._chosen[1]+1).mkMetricPacket()\
          if self._chosen and ip != self._chosen[0] \
          else InfoPacket(Tag.HI)
        self._dests[ip] = (pkt, False)

  def addDest(self, ip : str, state : bool = False) -> None:
    with self._lockDests:
      self._dests[ip] = (None,state)

  def addEntry(self, ip : str, metric : int) -> bool:
    newChosen = False
    with self._lockDests:
      with self._lockChosen:
        # Se não existe escolhido
        if self._chosen is None:
          self._chosen = (ip, metric)
          # Indicar alteração
          newChosen = True
        # Se existe escolhido
        else:
          chosenIp, chosenMetric = self._chosen
          # Se o escolhido atualizou a métrica
          if ip == chosenIp:
            # Se o escolhido melhorou a métrica
            if metric < chosenMetric:
              # Indicar alteração
              self._chosen = (ip, metric)
            # Se o escolhido piorou métrica
            elif metric > chosenMetric:
              # Escolher melhor de entre os substitutos
              with self._lockSubs:
                self._subs[ip] = metric
                newIp = min(self._subs, key=self._subs.get)
                self._chosen = (newIp, self._subs.pop(newIp))
            newChosen = True
          # Se um outro nodo tem métrica melhor
          elif metric < chosenMetric:
            with self._lockSubs:
              # Remover recebido dos substitutos
              self._subs.pop(ip, None)
              # Adicionar aos substitutos
              self._subs[chosenIp] = chosenMetric
            # Adicionar antigo aos destinos
            self._dests[chosenIp] = (None, False)
            # Atualizar escolhido
            self._chosen = (ip, metric)
            # Indicar alteração
            newChosen = True
          else:
            with self._lockSubs:
              # Adicionar aos substitutos
              self._subs[ip] = metric
            # Adicionar aos dests caso ainda não exista
            if ip not in self._dests:
              self._dests[ip] = (None, False)
      # Se o escolhido foi alterado
      if newChosen:
        # Remover dos destinos
        self._dests.pop(ip,None)
        # Enviar nova métrica para todos os destinos
        for k,v in self._dests.items():
          self._dests[k] = (MetricPacket.mkMetricPacket(src, metric+1), v[1])
      return newChosen
  
  def remove(self, ip : str) -> None:
    self._lockDests.acquire()
    self._dests.pop(ip, None)
    with self._lockSubs:
      self._subs.pop(ip, None)
      with self._lockChosen:
        self._lockDests.release()
        if self._chosen and self._chosen[0] == ip:
          if self._receiving[0]:
            self._receiving = (True, True)
          if self._subs:
            ip = min(self._subs, key=self._subs.get)
            self._chosen = (ip, self._subs.pop(ip))
          else:
            self._chosen = None

  def activateRoute(self, ip : str) -> str:
    self._lockDests.acquire()
    self._dests[ip] = (self._dests[ip][0], True)
    with self._lockChosen:
      self._lockDests.release()
      res = self._chosen[0]
      if not self._receiving[0]:
        self._receiving = (True, True)
    return res

  def deactivateRoute(self, ip : str) -> bool:
    res = False
    with self._lockDests:
      if ip in self._dests:
        self._dests[ip] = (self._dests[ip][0], False)
        if not any(map(lambda x: x[0], self._dests.values())):
          res = True
          with self._lockChosen:
            self._receiving = (False, True)
    return res

  def stopReceiving(self):
    with self._lockDests:
      for k,v in self._dests.items():
        self._dests[k] = (None, False)
      with self._lockChosen:
        if self._receiving[0]:
          self._receiving = (False, True)

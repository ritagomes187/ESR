from tkinter import *
import tkinter.messagebox, datetime
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os, time
sys.path.append("../")

from Misc.Util import INFO_PORT, DATA_PORT
from RTP.RTPPacket import RTPPacket
from InfoPacket.InfoPacket import InfoPacket
from InfoPacket.DelayPacket import DelayPacket
from InfoPacket.Tag import Tag
from InfoPacket.InvalidTag import InvalidTag

TIMEOUT_BEACON = 5
BUFFER_SIZE = RTPPacket.get_max_size()
INTERVAL_TIME  = 1

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client:
  INIT = 0
  READY = 1
  PLAYING = 2
  state = INIT
  
  SETUP = 0
  PLAY = 1
  PAUSE = 2
  TEARDOWN = 3
  
  # Initiation..
  def __init__(self, master, neighbor, socket = None):
    self.playEvent = None
    self.master = master
    self.master.protocol("WM_DELETE_WINDOW", self.handler)
    self.createWidgets()
    self.neighbor = neighbor
    self.fileName = "movie.Mjpeg"
    self.rtspSeq = 0
    self.sessionId = 0
    self.requestSent = -1
    self.teardownAcked = 0
    self.socket = socket
    self.servers : dict[str, tuple[int,float]] = {} #o int é a versão
    self.chosen = None 
    self._cTS()
    
    self.message = None
    self.lockMessage = threading.RLock()
    
  def createWidgets(self):
    """Build GUI."""
    # Create Setup button
    self.setup = Button(self.master, width=20, padx=3, pady=3)
    self.setup["text"] = "Setup"
    self.setup["command"] = self.setupMovie
    self.setup.grid(row=1, column=0, padx=2, pady=2)
    
    # Create Play button		
    self.start = Button(self.master, width=20, padx=3, pady=3)
    self.start["text"] = "Play"
    self.start["command"] = self.playMovie
    self.start.grid(row=1, column=1, padx=2, pady=2)
    
    # Create Pause button			
    self.pause = Button(self.master, width=20, padx=3, pady=3)
    self.pause["text"] = "Pause"
    self.pause["command"] = self.pauseMovie
    self.pause.grid(row=1, column=2, padx=2, pady=2)
    
    # Create Teardown button
    self.teardown = Button(self.master, width=20, padx=3, pady=3)
    self.teardown["text"] = "Teardown"
    self.teardown["command"] =  self.exitClient
    self.teardown.grid(row=1, column=3, padx=2, pady=2)
    
    # Create a label to display the movie
    self.label = Label(self.master, height=19)
    self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
  
  def _cTS(self):
    threading.Thread(target=self.connectToServer, daemon=True).start()

  def minD(self):
    key = ''
    min = list(self.servers.items())[0][1][1]
    for s,t in self.servers.items():
      if min >= t[1]:
        key = s
        min = t[1]
    return key

  def setupMovie(self):
    """Setup button handler."""
    if self.state == self.INIT:
      self.chosen = self.minD()
      self.sendRtspRequest(self.SETUP)
  
  def exitClient(self):
    """Teardown button handler."""
    self.sendRtspRequest(self.TEARDOWN)
    self.master.destroy() # Close the gui window
    os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video

  def pauseMovie(self):
    """Pause button handler."""
    if self.state == self.PLAYING:
      self.sendRtspRequest(self.PAUSE)

  def playMovie(self):
    """Play button handler."""
    if self.state == self.READY:
      # Create a new thread to listen for RTP packets
      threading.Thread(target=self.listenRtp, daemon=True).start()
      self.playEvent = threading.Event()
      self.playEvent.clear()
      self.sendRtspRequest(self.PLAY)
  
  def listenRtp(self):		
    """Listen for RTP packets."""
    while True:
      try:
        data = self.rtpSocket.recv(BUFFER_SIZE)
        if data:
          pkt = RTPPacket.decode(data)
          self.updateMovie(self.writeFrame(pkt.payload))
      except:
        # Stop listening upon requesting PAUSE or TEARDOWN
        if self.playEvent and self.playEvent.isSet(): 
          break
        
        # Upon receiving ACK for TEARDOWN request,
        # close the RTP socket
        if self.teardownAcked == 1:
          self.rtpSocket.shutdown(socket.SHUT_RDWR)
          self.rtpSocket.close()
          break
          
  def writeFrame(self, data):
    """Write the received frame to a temp image file. Return the image file."""
    cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
    file = open(cachename, "wb")
    file.write(data)
    file.close()
    
    return cachename
  
  def updateMovie(self, imageFile):
    """Update the image file as video frame in the GUI."""
    photo = ImageTk.PhotoImage(Image.open(imageFile))
    self.label.configure(image = photo, height=288)
    self.label.image = photo
    
  def firstMessage(self):
    with self.lockMessage:
      self.message = InfoPacket(Tag.HI)

  def popMessage(self):
    with self.lockMessage:
      try:
        return self.message
      finally:
        self.message = None

  def delayHandler(self,infp):
    dpk = DelayPacket.fromInfoPacket(infp)
    time = datetime.datetime.now().timestamp() 
    delay = time - dpk.timestamp
    if dpk.src in self.servers.keys() and (self.servers[dpk.src][0] < dpk.vs):
       self.servers[dpk.src] = (dpk.vs, delay)
    if dpk.src not in self.servers.keys():
       self.servers[dpk.src] = (dpk.vs, delay)

  def default(self, payload):
    pass

  def connectToServer(self):
    """Connect to the Server. Start a new RTSP/TCP session."""
    try:
      if self.socket is None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.neighbor, INFO_PORT))
        print("connect")

      with self.socket:
        self.firstMessage()
        #threading.Thread(target=self.delayHandler, daemon=True).start()
        while True:
          msg = self.popMessage()
          infp = msg if msg else InfoPacket(Tag.ALIVE)
          self.socket.sendall(infp.encode())
          

          time.sleep(INTERVAL_TIME)
          try:
            msg = self.socket.recv(256)
            infp = InfoPacket.decode(msg)
            print((self.neighbor, INFO_PORT), infp)
            if infp.tag == Tag.DELAY:
              self.delayHandler(infp)
            # ignore message
          except InvalidTag:
            pass

          time.sleep(INTERVAL_TIME)
    except:
      messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.neighbor)

  def sendRtspRequest(self, requestCode):
    """Send RTSP request to the server."""
    request = None
    # Setup request
    if requestCode == self.SETUP and self.state == self.INIT:
      request = Tag.PLAY

      # Keep track of the sent request.
      self.requestSent = self.SETUP
    
    # Play request
    elif requestCode == self.PLAY and self.state == self.READY:
      print('\nPLAY event\n')
      
      # request = Tag.PLAY

      # Keep track of the sent request.
      self.requestSent = self.PLAY
    
    # Pause request
    elif requestCode == self.PAUSE and self.state == self.PLAYING:
      print('\nPAUSE event\n')
      # Keep track of the sent request.
      self.requestSent = self.PAUSE

      request = Tag.STOP
      
    # Teardown request
    elif requestCode == self.TEARDOWN and not self.state == self.INIT:
      print('\nTEARDOWN event\n')
      
      request = Tag.STOP

      # Keep track of the sent request.
      self.requestSent = self.TEARDOWN
    else:
      return
    
    if self.requestSent == self.SETUP:
      # Update RTSP state.
      self.state = self.READY
      
      # Open RTP port.
      threading.Thread(target=self.openRtpPort, daemon=True).start()
    elif self.requestSent == self.PLAY:
      self.state = self.PLAYING
      print('\nPLAY sent\n')
    elif self.requestSent == self.PAUSE:
      self.state = self.READY
      
      # The play thread exits. A new thread is created on resume.
      self.playEvent.set()
    elif self.requestSent == self.TEARDOWN:
      self.state = self.INIT
      
      # Flag the teardownAcked to close the socket.
      self.teardownAcked = 1 

    if request:
      with self.lockMessage:
        self.message = InfoPacket.mkPSPacket(request,self.chosen)
    
  def openRtpPort(self):
    """Open RTP socket binded to a specified port."""
    #-------------
    # TO COMPLETE
    #-------------
    # Create a new datagram socket to receive RTP packets from the server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Set the timeout value of the socket to 0.5sec
    # self.rtpSocket.settimeout(0.5)
    
    try:
      # Bind the socket to the address using the RTP port given by the client user
      s.bind(("",DATA_PORT))
      s.listen()
      conn, addr = s.accept()
      self.rtpSocket = conn
      print('\nBind \n')
    except:
      messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' % DATA_PORT)

  def handler(self):
    """Handler on explicitly closing the GUI window."""
    self.pauseMovie()
    if messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
      self.exitClient()
    else: # When the user presses cancel, resume playing.
      self.playMovie()


import sys
from tkinter import Tk
from Client import Client

if __name__ == "__main__":
  try:
    neighborIP = sys.argv[1]
  except:
    print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")	
  
  root = Tk()
  
  # Create a new client
  app = Client(root, neighborIP)
  app.master.title("RTPClient")	
  root.mainloop()
  

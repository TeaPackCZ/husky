#!/usr/bin/python
"""
  Light weight wrapper to Husky
  usage:
     ./husky.py <task> [<replay log file> [F|FF]]
"""

import sys
import serial
import struct
from logit import *
from crc16 import ccitt_checksum as checksum

REQ_PLATFORM_INFO = 0x4001
REQ_FIRMWARE_INFO = 0x4003

SET_DIFFERENTIAL_OUTPUT = 0x0202

class Husky:
  def __init__( self, com ):
    self.com = com
    self.timestamp = 0

  def sendPacket( self, messageType, data = "" ):
    packet = struct.pack( '=BBBBIBHB',
    0xAA,           # SAH
    len(data)+11,   # data length + compliment
    255-len(data)-11,
    0,              # version (in doc is used version 1, but sample code sends 0)
    self.timestamp, # unique number for ACK
    0,              # flags
    messageType,    # 16bit
    0x55 )          # STX - data start
    packet += data
    packet += struct.pack("H", checksum( [ord(x) for x in packet] ))
    print repr(packet)
    self.timestamp += 1
    self.com.write( packet )

  def readPacket( self ):
    b = self.com.read(1)
    while b != chr(0xAA):
      print "skipping", hex(ord(b))
      b = self.com.read(1)
    length = ord(self.com.read(1))
    notLength = ord(self.com.read(1))
    assert length+notLength == 0xFF, (length, notLength)
    ret = ""
    for i in xrange(length):
      b = self.com.read(1)
      ret += b
    assert checksum( [0xAA, length, notLength] + [ord(x) for x in ret[:-2]] ) == ord(ret[-2]) + 256*ord(ret[-1])
    version, timestamp, flags, msgType, stx = struct.unpack("=BIBHB", ret[:9])
    assert version == 0x00, version # receiving ver0, but sending ver1
    assert flags == 0, flags
    assert stx == 0x55, stx
    return timestamp, msgType, ret[9:-2]


def main( com ):

  robot = Husky( com )
#  robot.sendPacket( REQ_PLATFORM_INFO )
#  robot.sendPacket( REQ_FIRMWARE_INFO, data=struct.pack("H",0) )
  robot.sendPacket( SET_DIFFERENTIAL_OUTPUT, data=struct.pack("hh", 3000, 3000) )
  for i in xrange(200):
    timestamp, msgType, data = robot.readPacket()
    if msgType == 0x8004:
      # System status data
      uptime, numMeas = struct.unpack( "=IB", data[:5] )
      data = data[5:]
      assert numMeas == 3, numMeas
      volt1, volt2, volt3, numMeas = struct.unpack( "hhhB", data[:6+1] )
      data = data[6+1:]
      print volt1/100., volt2/100., volt3/100., "|",
      assert numMeas == 3, numMeas
      cur1, cur2, cur3, numMeas = struct.unpack( "hhhB", data[:6+1] )
      data = data[6+1:]
      print cur1/100., cur2/100., cur3/100., "|",
      assert numMeas == 4, numMeas
      t1, t2, t3, t4 = struct.unpack( "hhhh", data )
      print t1/100., t2/100., t3/100., t4/100.
    if msgType == 0x8005:
      # Power system status data
      batNum, batState, batCap, batDesc = struct.unpack("=BHHB", data )
      assert batNum == 1, batNum
      assert batDesc == 0xC2, hex(batDesc) # present, in use, Lead-acid battery
      print batState, batCap
    if msgType == 0x8800:
      # Encoder data
      enc = struct.unpack( "=Biihh", data ) # expected 2 encoders - position and speed
      print "ENC", enc
    

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print __doc__
    sys.exit(1)
  filename = None
  com = None
  if len(sys.argv) > 2:
    replayAssert = True
    filename = sys.argv[2]
    if len(sys.argv) > 3:
      assert sys.argv[3] in ['F','FF']
      if sys.argv[2] == 'F':
        replayAssert = False
      else:
        com = ReplyLogInputsOnly( filename )
  if filename:
    if com == None:
      com = ReplayLog( filename, assertWrite=replayAssert )
  else:
    com = LogIt( serial.Serial( '/dev/ttyUSB1', 115200 ) )
  main( com )


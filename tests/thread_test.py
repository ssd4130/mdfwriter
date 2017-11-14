from mdf import *
import struct
import threading
import math

mdf = MDF('output', 'sadaleo', 'TestProject', 'TestDUT')
dej = DEJ('POWERWALL.compact.json')
messageList = dej.getMessages()


scpi_cg = ChannelGroup('SCPI_CG')
scpi_channel = Channel('SCPI_CN', 'SCPI_Units', 'Description')
scpi_cg.addChannel(scpi_channel)

scpi_cg2 = ChannelGroup('SCPI_CG2')
scpi_channel2 = Channel('SCPI_CN2', 'SCPI_Units2', 'Description2')
scpi_cg2.addChannel(scpi_channel2)

mdf.addChannelGroup(scpi_cg)
mdf.addChannelGroup(scpi_cg2)

mdf.addChannelGroup(messageList[0])
mdf.addChannelGroup(messageList[2])
mockdata = int(4278190080)

class threadWrite(threading.Thread):
    def __init__(self, cg, timestamp, data):
        threading.Thread.__init__(self)
        self.cg = cg
        self.timestamp = timestamp
        self.data = data

    def run(self):
        while self.timestamp < 99:
            i = 0
            data_cos = math.cos(i)
            data_sin = math.sin(i)
            mdf.write(self.cg, self.timestamp, [mockdata])
            self.timestamp += 1
            i += 1

recordList = mdf.getRecordList()
i = 0
mdf.startfile()
thread1 = threadWrite(mdf.cgList[0], i, [math.cos(i)])
thread2 = threadWrite(mdf.cgList[1], i, [math.sin(i)])
thread1.run()
thread2.run()
mdf.closefile()
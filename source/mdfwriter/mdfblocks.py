"""This file contains the block structures for the MDF file to be written correctly. Altering contents of file
can result in writing a corrupt file.
Author: Samuel Daleo, III"""
import time
from .utils import formatstring


class IDBlock:
    FILEID = "MDF     "
    FORMATID = "3.31    "
    PROGRAMID = "SAMDALEO"
    BYTEORDER = 0
    FLOATFORMAT = 0
    VERSIONNO = 331
    RESERVED = formatstring("", 34)
    BLOCKSIZE = 64

    def __init__(self):
        pass


class HDBlock:
    BLOCKID = "HD"
    BLOCKSIZE = 164
    ORG = "TESLA                           "

    def __init__(self, author, project, dut):
        self.firstDGPointer = 228
        self.firstTXPointer = 228
        self.firstPRPointer = 0
        self.numberOfDGs = 1
        self.date = time.strftime('%d' + ":" + "%m" + ":" + "%Y")
        self.time = time.strftime('%X')
        self.author = formatstring(author, 32)
        self.project = formatstring(project, 32)
        self.dut = formatstring(dut, 32)


class TXBlock:
    BLOCKID = "TX"

    def __init__(self, text):
        self.text = text
        self.blocksize = len(text) + 4


class DGBlock:
    BLOCKID = "DG"
    BLOCKSIZE = 28

    def __init__(self):
        self.nextDGPointer = 0
        self.nextCGPointer = 256
        self.reserved = 0
        self.dataPointer = 0
        self.numberofCGs = 0
        self.numberofRecordIDs = 1  # Record ID before each data record


class CGBlock:
    BLOCKID = "CG"
    BLOCKSIZE = 26

    def __init__(self, dg_block, record_id):
        self.cnBlockList = []
        self.nextCGPointer = 0
        self.CNPointer = 0
        self.TXPointer = 0
        self.recordID = record_id
        self.numberOfChannels = 0
        self.data_size = 0
        self.numberOfRecords = 0
        self.name = ""
        self.isCAN = False
        self.isString = False
        dg_block.numberofCGs += 1

    def add_channel(self, channel):
            self.cnBlockList.append(channel)


class CNBlock:
    BLOCKID = "CN"
    BLOCKSIZE = 228

    def __init__(self, cg, channel_type, signal_name=None, signal_description=None):
        self.nextCNPointer = 0
        self.CCPointer = 0
        self.CEPointer = 0
        self.reserved = 0
        self.TXPointer = 0
        self.channelTitle = channel_type.upper()
        self.signal_name = chr(0)*32
        self.signal_description = chr(0)*128
        self.numberOfBits = 0
        self.firstBitNo = 64
        if channel_type == "TIME":
            self.channel_type = 1
            self.numberOfBits = 64
            self.firstBitNo = 0
            self.signal_name = formatstring("TimeChannel", 32)
            self.signal_description = formatstring(signal_description, 128)
            self.signalType = 3
        elif channel_type == "DATA":
            self.channel_type = 0
            if signal_name is not None:
                self.signal_name = formatstring(signal_name, 32)
            else:
                self.signal_name = formatstring("", 32)
            if signal_description is not None:
                self.signal_description = formatstring(signal_description, 128)
            else:
                self.signal_description = formatstring("", 128)
            self.signalType = 2
            self.numberOfBits = 32
            start_bit = 0
            for i in range(len(cg.cnBlockList)):
                start_bit = start_bit + cg.cnBlockList[i].numberOfBits
                self.firstBitNo = start_bit
        elif channel_type == "CAN":
            self.channel_type = 0
            self.signal_name = formatstring(signal_name, 32)
            self.signal_description = formatstring(signal_description, 128)
            self.signalType = 0
            self.numberOfBits = 0
            self.firstBitNo = 64
        elif channel_type == "STRING":
            self.channel_type = 0
            self.signal_name = self.signal_name = formatstring(signal_name, 32)
            self.signal_description = formatstring(signal_description, 128)
            self.signalType = 7
            self.firstBitNo = 64
        self.valueRangeBool = 0    # 0 = false, 1 = true
        self.minValue = 0
        self.maxValue = 0
        self.sampleRate = 0
        self.ASAMPointer = 0
        self.TXPointer2 = 0
        self.byteOffset = 0


class CCBlock:
    BLOCKID = "CC"

    def __init__(self, cn, unit):
        self.valueRangeBool = 0    # 0 = false, 1 = true
        self.minValue = 0
        self.maxValue = 0
        self.conversionID = 0    # 0 = parametric, linear, 11 = VTAB
        self.blockSize = 46
        self.physUnit = formatstring(unit, 20)
        if cn.channelTitle == "TIME" or cn.channelTitle == "DATA":
            self.paramList = [0, 1]
            self.pairs = 2
            self.blockSize = 62
        else:
            self.paramList = []
            self.pairs = 0
            self.blockSize = 46


class CEBlock:
    BLOCKID = "CE"
    BLOCKSIZE = 128
    EXTENSIONID = 19

    def __init__(self, can_id, can_index, message_name, sender_name):
        self.canID = can_id
        self.canIndex = can_index
        self.messageName = formatstring(message_name, 36)
        self.senderName = formatstring(sender_name, 78)

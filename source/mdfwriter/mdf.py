"""Import this file to create MDF files. See documentation for class definitions and example use.
Author: Samuel Daleo, III"""

import struct
import json
import threading
import logging
from .mdfblocks import *

# This dictionary contains the format codes for the struct package to correctly format the binary output of input python
# datatypes.
STRUCT_TYPE = {'CHAR': struct.Struct('<c'),
               'UINT8': struct.Struct('<B'),
               'UINT16': struct.Struct('<H'),
               'UINT32': struct.Struct('<I'),
               'FLOAT': struct.Struct('<f'),
               'DOUBLE': struct.Struct('<d'),
               'BOOL': struct.Struct('<H'),
               'REAL': struct.Struct('<d'),
               'LINK': struct.Struct('<l'),
               'LONG': struct.Struct('<Q')}

logger = logging.getLogger(__name__)


class ChannelGroup(object):
    def __init__(self, name, description=None, channel_list=None):
        self.name = str(name)
        self.channel_list = self.signal_list = channel_list
        self.cgBlock = None
        if description is not None:
            self.description = description
        else:
            self.description = ""
        """Class for non-CAN record groups to be added to MDF.
        :param str name: The name of the Channel Group.
        :param str description: Description of the Channel Group.
        """

    def add_channel(self, channel):
        """Method for adding Channel object to ChannelGroup object. All Channel Objects must be added to the
        ChannelGroup before the ChannelGroup is added to the MDF.
        :param Channel channel: Channel object from Channel class to be added to the ChannelGroup.
        """
        self.channel_list.append(channel)


class CANmsg(ChannelGroup):
    def __init__(self, message_name, signal_list=None):
        self.name = message_name
        self.sender = ""
        self.signalList = signal_list
        self.messageID = 0
        self.length = 0
        self.index = 0
        self.cgBlock = None
        """Class for CAN messages to be added to MDF. Extends :class: ChannelGroup, and adds necessary properties
         for proper CAN data parsing in CANape
            :param str messagename: Name of CAN message
            :param [CANSignal] signal_list: List of CANSignal objects associated with CANmsg.
        """

    def add_signal(self, signal):
        """Used to add a Signal object to the CANmsg object.
        Note: Can not pass parent of Signal object 'Channel'.
        """
        self.signalList.append(signal)


class Channel(object):
    def __init__(self, name, units, description=None):
        self.name = name
        self.units = units
        self.description = description
        """Base class Channel.
        :param str name: Name of Channel
        :param str units: Units of Channel
        :param str description: Text description of Channel. Max 128 characters.
        """


class CANSignal(Channel):
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
        self.units = ""
        self.endianness = 0
        self.signedness = 0
        self.min = 0
        self.max = 0
        self.validRange = False
        self.scale = 0
        self.offset = 0
        self.startBit = 0
        self.is_enum = False
        self.value_dict = {}
        self.bitCount = 0
        """Child class of Channel with additional properties to make it compatabile with a CAN signal with a CANmesasge.
        :param str name: Name of the CANSignal
        :param str description: Description of the CANSignal, overrides the base class Channel's parameter 'description'
        """


class DEJ(object):
    def __init__(self, dej_path):
        with open(dej_path, 'r') as f:
            json_object = json.load(f)
        self.messageList = []
        for message in json_object['messages']:
            messagename = str(message)
            canmsg = CANmsg(messagename)
            canmsg.sender = str(json_object['messages'][messagename]['senders'][0])
            canmsg.messageID = int(json_object['messages'][messagename]['message_id'])
            canmsg.length = int(json_object['messages'][messagename]['length_bytes'])
            for signal in json_object['messages'][messagename]['signals']:
                signalname = str(signal)
                cansignal = CANSignal(signalname)
                if str(json_object['messages'][messagename]['signals'][signalname]['endianness']) == 'LITTLE':
                    cansignal.endianness = 0
                elif str(json_object['messages'][messagename]['signals'][signalname]['endianness']) == 'BIG':
                    cansignal.endianness = 1
                if str(json_object['messages'][messagename]['signals'][signalname]['signedness']) == 'UNSIGNED':
                    cansignal.signedness = 0
                elif str(json_object['messages'][messagename]['signals'][signalname]['signedness']) == 'SIGNED':
                    cansignal.signedness = 1
                cansignal.min = int(json_object['messages'][messagename]['signals'][signalname]['min'])
                cansignal.max = int(json_object['messages'][messagename]['signals'][signalname]['max'])
                if cansignal.min != 0 and cansignal.max != 0:
                    cansignal.validRange = True
                cansignal.startBit = int(json_object['messages'][messagename]['signals'][signalname]['start_position'])
                cansignal.units = str(json_object['messages'][messagename]['signals'][signalname]['units'])
                if 'value_description' in json_object['messages'][messagename]['signals'][signalname]:
                    cansignal.is_enum = True
                    cansignal.value_dict = json_object['messages'][messagename]['signals'][signalname]['value_description']
                cansignal.bitCount = json_object['messages'][messagename]['signals'][signalname]['width']
                cansignal.scale = json_object['messages'][messagename]['signals'][signalname]['scale']
                canmsg.signalList.append(cansignal)
            self.messageList.append(canmsg)
        """DEJ Class used to parse DEJ JSON file and store information as CANmsg objects
        with their respective CAN Signal objects.
        :param str dej_path: Path to .json DEJ file
        """

    def get_message_list(self):
        return self.messageList


class MDF(object):
    HEADER_SIZE = 228  # bytes

    def __init__(self, file_name, author, project, dut, file_description=None):
        self.IDBlock = IDBlock()
        self.HDBlock = HDBlock(author, project, dut)
        self.TXBlock = TXBlock(formatstring(file_description, len(file_description)+1))
        self.HDBlock.firstDGPointer = self.HEADER_SIZE + self.TXBlock.blocksize
        self.DGBlock = DGBlock()
        self.DGBlock.nextCGPointer += self.TXBlock.blocksize
        self.cgBlockList = []
        self.cnBlockList = []
        self.cc_blockList = []
        self.ceBlockList = []
        self.lock = threading.Lock()
        self.cgPointers = {}
        self.cnPointers = {}
        self.cnTypeList = []
        self.datapointer = 0
        self.timepointer = 0
        self.channelGroupDictionary = {}
        self.fileIndex = 1
        self.file = self.open_file(file_name)
        self.filename = file_name
        self.dataRecordCount = 0
        # self.blankChannelGroup = ChannelGroup('Blank Channel Group')
        # self.addChannelGroup(self.blankChannelGroup)   #See docstring
        """Main class of package. MDF object that holds all necessary information to write file correctly.
            Note Line 170: The initialization adds a blank ChannelGroup to the MDF file to avoid a bug with CANape.
            If the file contains only one ChannelGroup, it will be considered "sorted" and will not parse correctly.
        :param str filename: Name of file to be created (.mdf automatically appended)
        :param str author: Creator of file
        :param str project: Name of Project of test
        :param str dut: Device under test
        """

    def add_channel_group(self, channelgroup):
        """Method to add ChannelGroup object to MDF.
        All ChannelGroup objects (or CANmsg objects) must be added to MDF before file header is written.
        :param ChannelGroup channelgroup: New ChannelGroup/CANmsg object to be added to MDF."""
        string_size_limit = 32
        channel_group = CGBlock(self.DGBlock, len(self.cgBlockList)+1)
        channel_group.name = channelgroup.name
        self.cgBlockList.append(channel_group)
        self.channelGroupDictionary[channel_group.name] = channel_group
        # Creates a mandatory time channel for the new channel group to be added to MDF
        time_channel = CNBlock(channel_group, "TIME")
        time_channel.signalname = formatstring("Zeitkanal", string_size_limit)
        channel_group.cnBlockList.append(time_channel)
        self.cnBlockList.append(time_channel)
        index = len(self.cgBlockList) - 1
        self.cgBlockList[index].numberOfChannels += 1
        cc_time = CCBlock(time_channel, 's')
        self.cc_blockList.append(cc_time)
        if isinstance(channelgroup, CANmsg):
            channel_group.isCAN = True
            for channel in channelgroup.signalList:
                signal_channel = CNBlock(channel_group, "CAN", str(channel.name), str(channel.description))
                signal_channel.valueRangeBool = 1 if channel.validRange else 0
                signal_channel.minValue = channel.min
                signal_channel.maxValue = channel.max
                signal_channel.numberOfBits = channel.bitCount
                signal_channel.firstBitNo += channel.startBit
                channel_group.cnBlockList.append(signal_channel)
                self.cnBlockList.append(signal_channel)
                self.cgBlockList[index].numberOfChannels += 1
                cc_block = CCBlock(signal_channel, channel.units)
                cc_block.valueRangeBool = 1 if channel.validRange else 0
                cc_block.minValue = channel.min
                cc_block.maxValue = channel.max
                if len(channel.value_dict) > 1:
                    cc_block.conversionID = 11  # bytes
                    for x in range(len(channel.value_dict)):
                        cc_block.paramList.append(formatstring(channel.value_dict.values()[x], string_size_limit))
                        cc_block.paramList.append(float(channel.value_dict.keys()[x]))
                        cc_block.blockSize += 40  # bytes
                    cc_block.pairs = len(cc_block.paramList) / 2
                else:
                    cc_block.conversionID = 0
                    cc_block.paramList = [float(channel.offset), float(channel.scale)]
                    cc_block.blockSize = 62  # bytes
                    cc_block.pairs = 2
                self.cc_blockList.append(cc_block)
                ce = CEBlock(channelgroup.messageID, channelgroup.index, "SenderName", "SenderDescription")
                self.ceBlockList.append(ce)
        elif isinstance(channelgroup, ChannelGroup):
            for channel in channelgroup.channel_list:
                    data_channel = CNBlock(channel_group, "DATA", str(channel.name), str(channel.description))
                    channel_group.cnBlockList.append(data_channel)
                    self.cnBlockList.append(data_channel)
                    self.cgBlockList[index].numberOfChannels += 1
                    cc_block = CCBlock(data_channel, channel.units)
                    self.cc_blockList.append(cc_block)

    def get_channelgroup_list(self):
        """Use this method to get the list of ChannelGroup names. Names are used to reference low level structures
            in the file when using the mdf.write() method.
        """
        return self.channelGroupDictionary.keys()

    def open_file(self, file_name):
        """Automatically called upon instantation of MDF object.
        :param str file_name: Name of file to be created.
        """
        if self.fileIndex == 1:
            self.file = open(str(file_name), 'wb+')
            logger.debug(str(file_name) + ".mdf created @" + str(time.strftime("%X")))
        elif self.fileIndex > 1:
            self.file = open(str(file_name + str(self.fileIndex) + ".mdf"), 'wb+')
            logger.debug(str(file_name) + str(self.fileIndex) + ".mdf created @"
                         + str(time.strftime("%X")))
        return self.file

    def start_file(self):
        """Method to write header and respective pointers to tie everything together."""
        print("Writing header...")
        self._write_header()
        self._write_pointers()

    def close_file(self):
        """Method to close file once data is finished being written. Must be called, otherwise file will corrupt."""
        print("Closing MDF...")
        for k in range(len(self.cgBlockList)):
            location = self.cgPointers['cg' + str(k + 1)]['numberOfRecordsPointer']
            count = self.cgBlockList[k].numberOfRecords  # List of records for each CG
            self.file.seek(location)
            self.file.write(STRUCT_TYPE['UINT32'].pack(count))

        for l in range(len(self.cgBlockList)):
            location = self.cgPointers['cg' + str(l + 1)]['dataSizePointer']
            self.file.seek(location)
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(self.cgBlockList[l].data_size))
        self.file.close()
        print("MDF Closed Successfully!")

    def import_dej(self, dej_path):
        """Method to import a DEJ into the MDF.
        :param str dej_path: System path to .dej file"""
        dej = DEJ(dej_path)
        messages = dej.get_message_list()
        for message in messages:
            self.add_channel_group(message)

    def write(self, channelgroup_name, timestamp_offset, value):
        """Method to write data record to file. Only to be called once file is open and header is written.
        :param str channelgroup_name: Name of ChannelGroup object in which the data belongs to.
        :param int timestamp_offset: Decimal offset from timestamp in header.
        :param list value: Either raw CAN message data from CAN bus, or a List []
        of data for each signal in ChannelGroup"""
        string_size_limit = 32
        file_size_limit = 1000000000  # bytes, 1000000000 == 1 GB
        self.lock.acquire()
        try:
            cg = self.channelGroupDictionary[channelgroup_name]
            index = cg.recordID - 1
            packet = STRUCT_TYPE['UINT8'].pack(cg.recordID)
            packet += STRUCT_TYPE['DOUBLE'].pack(timestamp_offset)
            packetsize = 8   # Starts with 8 bytes for timestamp.
            if cg.isCAN:
                packet += ('<Q', value)
                packetsize += 8    # 8 bytes
            else:
                for datum in value:
                    if type(datum) == str:
                        datum = formatstring(datum, string_size_limit)
                        for letter in datum:
                            packet += STRUCT_TYPE['CHAR'].pack(letter)
                        packetsize += string_size_limit
                    else:
                        packet += STRUCT_TYPE['FLOAT'].pack(float(datum))
                        packetsize += 4
            # Checks filesize limit of 1GB. If file is over limit, starts new file.
            # 1GB limit chosen due to third-party package having difficult time parsing files larger than that
            if self.file.tell() > file_size_limit:
                self.close_file()
                self.fileIndex = int(self.filename[len(self.filename)-5]) + 1
                self.filename = self.filename[0:len(self.filename)-5] + str(self.fileIndex) + ".mdf"
                self.file = self.open_file(self.filename)
                self._write_header()
                self._write_pointers()
            self._write_string(packet)
            self.cgBlockList[index].numberOfRecords += 1
            self.cgBlockList[index].data_size = packetsize
            self.dataRecordCount += 1
        finally:
            self.lock.release()

    def define_start_time(self, timestamp):
        """To change timestamp in header. All time offsets in data block of file will reference this time.
        :param str timestamp: HH:MM:SS"""
        if type(timestamp) is str and timestamp[2] is ":" and timestamp[5] is ":":
            self.file.seek(self.timepointer)
            self.file.write(timestamp)

    def get_epoch_time(self):
        """Translates MDF spec timestamp format to epoch time for conversion to time offset float value"""
        datetime = self.HDBlock.date + " " + self.HDBlock.time
        epochtime = int(time.mktime(time.strptime(datetime, '%d:%m:%Y %H:%M:%S')))
        return epochtime

    def _write_header(self):
        """Private method that writes necessary file contents in a specific order. Should NOT be altered.
        This method creates a dictionary that homlds the various pointers that the _write_pointers method accesses after
        the header is written.
        Dictionary structure: { "cg#": {'cnCount': value},{'cgPointerPointer': value},{'cnPointerPointer': value},
                              {'dataSizePointer': value},{'numberOfRecordsPointer': value},{'numberOfRecords': value},
                                "cn#": {'cnPointerPointer': value}, {'ccPointerPointer': value},
                                {'cePointerPointer':  value}}"""
        self.file.seek(0)
        # ID Block
        self._write_string(self.IDBlock.FILEID)
        self._write_string(self.IDBlock.FORMATID)
        self._write_string(self.IDBlock.PROGRAMID)
        self._write_to_file(STRUCT_TYPE['UINT16'].pack(self.IDBlock.BYTEORDER))
        self._write_to_file(STRUCT_TYPE['UINT16'].pack(self.IDBlock.FLOATFORMAT))
        self._write_to_file(STRUCT_TYPE['UINT16'].pack(self.IDBlock.VERSIONNO))
        self._write_string(self.IDBlock.RESERVED)

        # HDBlock
        self._write_string(self.HDBlock.BLOCKID)
        self._write_to_file(STRUCT_TYPE['UINT16'].pack(self.HDBlock.BLOCKSIZE))
        self._write_to_file(STRUCT_TYPE['LINK'].pack(self.HDBlock.firstDGPointer))
        self._write_to_file(STRUCT_TYPE['LINK'].pack(self.HDBlock.firstTXPointer))
        self._write_to_file(STRUCT_TYPE['LINK'].pack(self.HDBlock.firstPRPointer))
        self._write_to_file(STRUCT_TYPE['UINT16'].pack(self.HDBlock.numberOfDGs))
        self._write_string(self.HDBlock.date)
        self.timepointer = self.file.tell()
        self._write_string(self.HDBlock.time)
        self._write_string(self.HDBlock.author)
        self._write_string(self.HDBlock.ORG)
        self._write_string(self.HDBlock.project)
        self._write_string(self.HDBlock.dut)

        # TXBlock
        self._write_string(self.TXBlock.BLOCKID)
        self._write_to_file(STRUCT_TYPE['UINT16'].pack(self.TXBlock.blocksize))
        self._write_string(self.TXBlock.text)

        # DGBlock
        self._write_string(self.DGBlock.BLOCKID)
        self._write_to_file(STRUCT_TYPE['UINT16'].pack(self.DGBlock.BLOCKSIZE))
        self._write_to_file(STRUCT_TYPE['LINK'].pack(self.DGBlock.nextDGPointer))
        self._write_to_file(STRUCT_TYPE['LINK'].pack(self.DGBlock.nextCGPointer))
        self._write_to_file(STRUCT_TYPE['LINK'].pack(self.DGBlock.reserved))
        data_pointer_pointer = self.file.tell()
        self._write_to_file(STRUCT_TYPE['LINK'].pack(self.DGBlock.dataPointer))
        self._write_to_file(STRUCT_TYPE['UINT16'].pack(self.DGBlock.numberofCGs))
        self._write_to_file(STRUCT_TYPE['UINT16'].pack(self.DGBlock.numberofRecordIDs))
        self._write_to_file(STRUCT_TYPE['UINT32'].pack(self.DGBlock.reserved))

        # CGBlock
        self.cgPointers['cgCount'] = len(self.cgBlockList)
        for list_index, cg_block in enumerate(self.cgBlockList):
            self.cgPointers['cg' + str(list_index + 1)] = {}
            self.cgPointers['cg' + str(list_index + 1)]['cnCount'] = cg_block.numberOfChannels
            self._write_string(cg_block.BLOCKID)
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cg_block.BLOCKSIZE))
            self.cgPointers['cg' + str(list_index + 1)]['cgPointerPointer'] = self.file.tell()
            self._write_to_file(STRUCT_TYPE['LINK'].pack(cg_block.nextCGPointer))
            self.cgPointers['cg' + str(list_index + 1)]['cnPointerPointer'] = self.file.tell()
            self._write_to_file(STRUCT_TYPE['LINK'].pack(cg_block.CNPointer))
            self._write_to_file(STRUCT_TYPE['LINK'].pack(cg_block.TXPointer))
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cg_block.recordID))
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cg_block.numberOfChannels))
            self.cgPointers['cg' + str(list_index + 1)]['dataSizePointer'] = self.file.tell()
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cg_block.data_size))
            self.cgPointers['cg' + str(list_index + 1)]['numberOfRecordsPointer'] = self.file.tell()
            self.cgPointers['cg' + str(list_index + 1)]['numberOfRecords'] = 0
            self._write_to_file(STRUCT_TYPE['UINT32'].pack(cg_block.numberOfRecords))

        # CNBlock
        self.cnPointers['numberOfCNs'] = len(self.cnBlockList)
        for list_index, cn_block in enumerate(self.cnBlockList):
            self.cnPointers['cn' + str(list_index + 1)] = {}
            if cn_block.channelType == 0:
                self.cnTypeList.append(0)
            if cn_block.channelType == 1:
                self.cnTypeList.append(1)
            self._write_string(cn_block.BLOCKID)
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cn_block.BLOCKSIZE))
            self.cnPointers['cn' + str(list_index + 1)]['cnPointerPointer'] = self.file.tell()
            self._write_to_file(STRUCT_TYPE['LINK'].pack(cn_block.nextCNPointer))
            self.cnPointers['cn' + str(list_index + 1)]['ccPointerPointer'] = self.file.tell()
            self._write_to_file(STRUCT_TYPE['LINK'].pack(cn_block.CCPointer))
            self.cnPointers['cn' + str(list_index + 1)]['cePointerPointer'] = self.file.tell()
            self._write_to_file(STRUCT_TYPE['LINK'].pack(cn_block.CEPointer))
            self._write_to_file(STRUCT_TYPE['LINK'].pack(cn_block.reserved))
            self._write_to_file(STRUCT_TYPE['LINK'].pack(cn_block.TXPointer))
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cn_block.channelType))
            self._write_string(cn_block.signalName)
            self._write_string(cn_block.signalDescription)
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cn_block.firstBitNo))
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cn_block.numberOfBits))
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cn_block.signalType))
            self._write_to_file(STRUCT_TYPE['BOOL'].pack(cn_block.valueRangeBool))
            self._write_to_file(STRUCT_TYPE['REAL'].pack(cn_block.minValue))
            self._write_to_file(STRUCT_TYPE['REAL'].pack(cn_block.maxValue))
            self._write_to_file(STRUCT_TYPE['REAL'].pack(cn_block.sampleRate))
            self._write_to_file(STRUCT_TYPE['LINK'].pack(cn_block.ASAMPointer))
            self._write_to_file(STRUCT_TYPE['LINK'].pack(cn_block.TXPointer2))
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cn_block.byteOffset))

        # CCBlock
        for list_index, cc_block in enumerate(self.cc_blockList):
            self._write_string(cc_block.BLOCKID)
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cc_block.blockSize))
            self._write_to_file(STRUCT_TYPE['BOOL'].pack(cc_block.valueRangeBool))
            self._write_to_file(STRUCT_TYPE['REAL'].pack(cc_block.minValue))
            self._write_to_file(STRUCT_TYPE['REAL'].pack(cc_block.maxValue))
            self._write_string(cc_block.physUnit)
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cc_block.conversionID))
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(cc_block.pairs))
            if cc_block.conversionID == 0:
                for p in range(len(cc_block.paramList)):
                    self._write_to_file(STRUCT_TYPE['REAL'].pack(cc_block.paramList[p]))
            elif cc_block.conversionID == 11:
                for s in six.xrange(0, len(cc_block.paramList), 2):
                    self._write_string(str(cc_block.paramList[s]))
                    self._write_to_file(STRUCT_TYPE['REAL'].pack(cc_block.paramList[s + 1]))

        # CEBlock
        self.cecount = 0
        for list_index, ce_block in enumerate(self.ceBlockList):
            self._write_string(ce_block.BLOCKID)
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(ce_block.BLOCKSIZE))
            self._write_to_file(STRUCT_TYPE['UINT16'].pack(ce_block.EXTENSIONID))
            self._write_to_file(STRUCT_TYPE['UINT32'].pack(ce_block.canID))
            self._write_to_file(STRUCT_TYPE['UINT32'].pack(ce_block.canIndex))
            self._write_string(ce_block.messagename)
            self._write_string(ce_block.senderName)
        self.file.seek(0, 2)
        datapointer = self.file.tell()
        self.file.seek(data_pointer_pointer)
        self._write_to_file(STRUCT_TYPE['LINK'].pack(datapointer))
        self.file.seek(0,2)

    def _write_pointers(self):
        """Called after the _writeHeaders() function call. This will tie blocks together by populating space in each
        block with necessary pointer value."""
        # CGBlock Pointers
        ccblock_size_list = []

        # These constants were calculated from spec sheet
        size_of_cnblock = 228
        size_offset_of_information_header = 256
        size_of_cgblock = 26
        cn_block_offset_minus_pointer_location = 224
        size_of_ceblock = 128

        ccblock_size = 0
        for list_index, cc_block in enumerate(self.cc_blockList):
            ccblock_size += cc_block.blockSize
            ccblock_size_list.append(ccblock_size)
        cn_offset = 0  # Instantiate variable before start
        pointer = 0

        # cgPointerPointer
        for i in range(len(self.cgBlockList)):
            location = self.cgPointers['cg' + str(i + 1)]['cgPointerPointer']
            if len(self.cgBlockList) == 1:
                pointer = 0
            elif len(self.cgBlockList) > 1:
                if i + 1 is not len(self.cgBlockList):
                    pointer = size_offset_of_information_header + self.TXBlock.blocksize + size_of_cgblock * (i + 1)
                elif i + 1 is len(self.cgBlockList):
                    pointer = 0
            self.file.seek(location)
            self.file.write(STRUCT_TYPE['LINK'].pack(pointer))

        # cnPointerPointer #
        for j in range(len(self.cgBlockList)):
            location = self.cgPointers['cg' + str(j + 1)]['cnPointerPointer']
            if j > 0:
                if j == 1:
                    cn_offset = self.cgPointers['cg' + str(j)]['cnCount']*size_of_cnblock
                else:
                    cn_offset += size_of_cnblock * self.cgPointers['cg' + str(j)]['cnCount']
            pointer = size_offset_of_information_header + self.TXBlock.blocksize \
                      + size_of_cgblock * len(self.cgBlockList) + cn_offset
            self.file.seek(location)
            self.file.write(STRUCT_TYPE['LINK'].pack(pointer))

        # CNBlock Pointers
        # ccPointer
        for l in range(len(self.cc_blockList)):
            if l > 0:
                ccoffset = ccblock_size_list[l-1]
            else:
                ccoffset = 0
            location = self.cnPointers['cn' + str(l + 1)]['ccPointerPointer']
            pointer = size_offset_of_information_header + self.TXBlock.blocksize + \
                size_of_cgblock * len(self.cgBlockList) + size_of_cnblock*len(self.cnBlockList) + ccoffset
            self.file.seek(location)
            self.file.write(STRUCT_TYPE['LINK'].pack(pointer))

        # nextCNPointer
        location = self.cnPointers['cn1']['cnPointerPointer']
        for m in range(len(self.cgBlockList)):
            cn_number = self.cgPointers['cg' + str(m + 1)]['cnCount']
            for n in range(cn_number):
                if n + 1 is not cn_number:
                    pointer = location + cn_block_offset_minus_pointer_location
                elif n + 1 is cn_number:
                    pointer = 0
                self.file.seek(location)
                self.file.write(STRUCT_TYPE['LINK'].pack(pointer))
                location += size_of_cnblock

        s = 0
        if len(self.ceBlockList) > 0:
            for t in range(len(self.cnBlockList)):
                location = self.cnPointers['cn' + str(t + 1)]['cePointerPointer']
                if self.cnBlockList[t].channelTitle == "CAN":
                    pointer = size_offset_of_information_header + self.TXBlock.blocksize + \
                              size_of_cgblock*len(self.cgBlockList) + size_of_cnblock*len(self.cnBlockList) + \
                              ccblock_size + size_of_ceblock*s
                    s += 1
                elif self.cnTypeList[t] == 1:
                    pointer = 0
                self.file.seek(location)
                self.file.write(STRUCT_TYPE['LINK'].pack(pointer))
        self.file.seek(0, 2)

    def _write_to_file(self, value):
        """Writes a value to a file by formatting it into the correct binary type using struct package."""
        self.file.write(value)

    def _write_string(self, s):
        """Specific method for writing python type string to file by formatting it to correct binary format."""
        if type(s) is str:
            for i in range(len(s)):
                self._write_to_file(STRUCT_TYPE['CHAR'].pack(s[i]))

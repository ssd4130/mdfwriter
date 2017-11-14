from mdfwriter.mdf import *
import unittest
import logging
import mdfreader

filename = 'test_output.mdf'
# class Test():

def channel_group_test():
    mdf = MDF(filename, 'sadaleo', 'UnitTest', 'UnitTest')
    channel_group_1 = ChannelGroup('Channel Group 1', 'Description')
    channel_group_2 = ChannelGroup('Channel Group 2', 'Description')
    channel_group_1.add_channel(Channel("Name", "Units", "Description"))
    channel_group_1.add_channel(Channel("Name2", "Units2", "Description2"))
    channel_group_2.add_channel(Channel("Name3", "Units3", "Description3"))
    channel_group_2.add_channel(Channel("Name4", "Units4", "Description4"))
    mdf.add_channel_group(channel_group_1)
    mdf.add_channel_group(channel_group_2)
    mdf.start_file()
    for i in range(10):
        mdf.write('Channel Group 1', i, [i])
        mdf.write('Channel Group 1', i, [i*2.4])
    mdf.close_file()
    mdf_file = mdfreader.mdf(filename)
    channel_list = mdf_file.masterChannelList
    print(channel_list)

if __name__ == '__main__':
    channel_group_test()
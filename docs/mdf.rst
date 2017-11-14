MDF.py
=======================================

Overview
--------
The main file in the mdfwriter package. Using the MDF class, a programmer can create an MDF object and add the necessary "ChannelGroup" objects that contain "Channel" objects to the MDF object. An MDF object can also absorb/import a DEJ containing information about the CAN data that will be logged to the file.

.. autoclass:: mdf.ChannelGroup
   :members:
.. autoclass:: mdf.Channel
   :members:
.. autoclass:: mdf.CANmsg
   :members:
.. autoclass:: mdf.CANSignal
   :members:
.. autoclass:: mdf.DEJ
   :members:
.. autoclass:: mdf.MDF
   :members:

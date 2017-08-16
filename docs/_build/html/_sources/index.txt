mdfwriter: A python tool to generate .mdf files for long-term data storage
==============================================================================

Author
--------
Samuel Daleo

Work email: sadaleo@tesla.com (depreciated as of March 17th 2017)

School email: dale9292@kettering.edu


Overview
---------
Mdfwriter is a python tool designed to automatically generate .mdf files which are used to store data for long-term use. The MDF specification from Vector can be found `here <https://vector.com/downloads/mdf_specification.pdf>`_. The mdf_writer library follows this specification to generate the low-level file structure contents given any number of user created "ChannelGroup" objects that contain "Channels" which contain data. The .MDF file is formatted to store "raw" CAN data in it's binary format and using Vector's CANape tool (or similar python packages), the data is parsed and presented in a way that can be used for data analysis. This package also allows a user to store any *other* types of data so long as the user follows the guidelines explained within this documentation.


Contents
---------

.. toctree::
   :maxdepth: 3

   mdf
   mdfblocks
   tests


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

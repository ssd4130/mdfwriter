from __future__ import absolute_import
__author__ = "sadaleo"

try:
    # version file populated by jenkins PyPi builder
    from ._version import __version__
except ImportError:
    __version__ = "unknown_local_version"

version = __version__

from .mdf import *

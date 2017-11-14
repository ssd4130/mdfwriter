import pytest
import unittest
import mdfwriter


class Test_Mdfwriter(unittest.TestCase):
    def test_ability_to_init_module(self):
        object = mdfwriter.core.Mdfwriter()
        assert isinstance(object, mdfwriter.core.Mdfwriter)

    # TODO implement tests. reference: http://doc.pytest.org/

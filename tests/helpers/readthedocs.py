# -*- coding: utf-8 -*-
"""Tests for the readthedocs helper."""
import unittest

import l2treviewtools.helpers.readthedocs as readthedocs_helper


class ReadthedocsHelperTest(unittest.TestCase):
  """Tests the readthedocs helper"""

  def testInitialize(self):
    """Tests that the helper can be initialized."""
    helper = readthedocs_helper.ReadTheDocsHelper(project=u'test')
    self.assertIsNotNone(helper)

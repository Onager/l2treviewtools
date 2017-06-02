# -*- coding: utf-8 -*-
"""Tests for the project helper."""
import unittest

import l2treviewtools.helpers.project as project_helper


class ProjectHelperTest(unittest.TestCase):
  """Tests the project helper"""

  def testInitialize(self):
    """Tests that the helper can be initialized."""
    helper = project_helper.ProjectHelper(
        u'/home/plaso/l2treviewtools/review.py')
    self.assertIsNotNone(helper)

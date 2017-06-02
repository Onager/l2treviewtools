# -*- coding: utf-8 -*-
"""Tests for the GitHub helper."""
import unittest

import l2treviewtools.helpers.github as github_helper


class GitHubHelperTest(unittest.TestCase):
  """Tests the command line helper"""

  def testInitialize(self):
    """Tests that the helper can be initialized."""
    helper = github_helper.GitHubHelper(
        organization='test', project='test_project')
    self.assertIsNotNone(helper)

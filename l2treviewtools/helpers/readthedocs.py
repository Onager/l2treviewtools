# -*- coding: utf-8 -*-
"""Helper for interacting with readthedocs."""

import logging

from l2treviewtools.helpers import url_lib
from l2treviewtools.lib import errors


class ReadTheDocsHelper(object):
  """Readthedocs helper."""

  def __init__(self, project):
    """Initializes a readthedocs helper.

    Args:
      project (str): github project name.
    """
    super(ReadTheDocsHelper, self).__init__()
    self._project = project
    self._url_lib_helper = url_lib.URLLibHelper()

  def TriggerBuild(self):
    """Triggers readthedocs to build the docs of the project.

    Returns:
      bool: True if the build was triggered.
    """
    readthedocs_url = u'https://readthedocs.org/build/{0:s}'.format(
        self._project)

    try:
      self._url_lib_helper.Request(readthedocs_url, post_data=b'')

    except errors.ConnectionError as exception:
      logging.warning(u'{0!s}'.format(exception))
      return False

    return True

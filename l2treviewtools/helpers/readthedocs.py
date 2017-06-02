# -*- coding: utf-8 -*-
"""Helper for interacting with readthedocs."""

import logging
import sys
# pylint: disable=import-error
# pylint: disable=no-name-in-module
if sys.version_info[0] < 3:
  # Use urllib2 here since this code should be able to be used by a default
  # Python set up. Otherwise usage of requests is preferred.
  import urllib2 as urllib_error
  import urllib2 as urllib_request
else:
  import urllib.error as urllib_error
  import urllib.request as urllib_request


class ReadTheDocsHelper(object):
  """Readthedocs helper."""

  def __init__(self, project):
    """Initializes a readthedocs helper.

    Args:
      project (str): github project name.
    """
    super(ReadTheDocsHelper, self).__init__()
    self._project = project

  def TriggerBuild(self):
    """Triggers readthedocs to build the docs of the project.

    Returns:
      bool: True if the build was triggered.
    """
    readthedocs_url = u'https://readthedocs.org/build/{0:s}'.format(
        self._project)

    request = urllib_request.Request(readthedocs_url)

    # This will change the request into a POST.
    request.add_data(b'')

    try:
      url_object = urllib_request.urlopen(request)
    except urllib_error.HTTPError as exception:
      logging.error(
          u'Failed triggering build with error: {0!s}'.format(
              exception))
      return False

    if url_object.code != 200:
      logging.error(
          u'Failed triggering build with status code: {0:d}'.format(
              url_object.code))
      return False

    return True

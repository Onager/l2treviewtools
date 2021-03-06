# -*- coding: utf-8 -*-
"""Helper for interacting with the Codereview upload.py tool."""

from __future__ import print_function
import json
import logging
import os
import random
import sys

# pylint: disable=import-error,no-name-in-module
if sys.version_info[0] < 3:
  import urllib2 as urllib_error
  import urllib as  urllib_parse
  import urllib2 as urllib_request
else:
  import urllib.error as urllib_error
  import urllib.parse as urllib_parse
  import urllib.request as urllib_request

# pylint: disable=wrong-import-position
from l2treviewtools.helpers import cli
from l2treviewtools.lib import upload as upload_tool


class UploadHelper(cli.CLIHelper):
  """Codereview upload.py command helper."""

  # yapf: disable

  _REVIEWERS_PER_PROJECT = {
      u'dfdatetime': frozenset([
          u'joachim.metz@gmail.com',
          u'onager@deerpie.com']),
      u'dfkinds': frozenset([
          u'joachim.metz@gmail.com',
          u'onager@deerpie.com']),
      u'dfvfs': frozenset([
          u'joachim.metz@gmail.com',
          u'onager@deerpie.com']),
      u'dfwinreg': frozenset([
          u'joachim.metz@gmail.com',
          u'onager@deerpie.com']),
      u'dftimewolf': frozenset([
          u'jberggren@gmail.com',
          u'someguyiknow@google.com',
          u'tomchop@gmail.com']),
      u'l2tpreg': frozenset([
          u'joachim.metz@gmail.com',
          u'onager@deerpie.com']),
      u'plaso': frozenset([
          u'aaronp@gmail.com',
          u'jberggren@gmail.com',
          u'joachim.metz@gmail.com',
          u'onager@deerpie.com',
          u'romaing@google.com'])}

  _REVIEWERS_DEFAULT = frozenset([
      u'jberggren@gmail.com',
      u'joachim.metz@gmail.com',
      u'onager@deerpie.com'])

  _REVIEWERS_CC = frozenset([
      u'kiddi@kiddaland.net',
      u'log2timeline-dev@googlegroups.com'])

  # yapf: enable

  def __init__(self, email_address, no_browser=False):
    """Initializes a codereview helper.

    Args:
      email_address (str): email address.
      no_browser (Optional[bool]): True if the functionality to use the
          webbrowser to get the OAuth token should be disabled.
    """
    super(UploadHelper, self).__init__()
    self._access_token = None
    self._email_address = email_address
    self._no_browser = no_browser
    self._upload_py_path = os.path.join(u'l2treviewtools', u'lib', u'upload.py')
    self._xsrf_token = None

  def _GetReviewer(self, project_name):
    """Determines the reviewer.

    Args:
      project_name (str): name of the project.

    Returns:
      str: email address of the reviewer that is used on codereview.
    """
    reviewers = list(
        self._REVIEWERS_PER_PROJECT.get(project_name, self._REVIEWERS_DEFAULT))

    try:
      reviewers.remove(self._email_address)
    except ValueError:
      pass

    random.shuffle(reviewers)

    return reviewers[0]

  def _GetReviewersOnCC(self, project_name, reviewer):
    """Determines the reviewers on CC.

    Args:
      project_name (str): name of the project.
      reviewer (str): email address of the reviewer that is used on codereview.

    Returns:
      str: comma separated email addresses.
    """
    reviewers_cc = set(
        self._REVIEWERS_PER_PROJECT.get(project_name, self._REVIEWERS_DEFAULT))
    reviewers_cc.update(self._REVIEWERS_CC)

    reviewers_cc.remove(reviewer)

    try:
      reviewers_cc.remove(self._email_address)
    except KeyError:
      pass

    return u','.join(reviewers_cc)

  def AddMergeMessage(self, issue_number, message):
    """Adds a merge message to the code review issue.

    Where the merge is a commit to the main project git repository.

    Args:
      issue_number (int|str): codereview issue number.
      message (str): message to add to the code review issue.

    Returns:
      bool: merge message was added to the code review issue.
    """
    codereview_access_token = self.GetAccessToken()
    xsrf_token = self.GetXSRFToken()
    if not codereview_access_token or not xsrf_token:
      return False

    codereview_url = b'https://codereview.appspot.com/{0!s}/publish'.format(
        issue_number)

    post_data = urllib_parse.urlencode({
        u'add_as_reviewer': u'False',
        u'message': message,
        u'message_only': u'True',
        u'no_redirect': 'True',
        u'send_mail': 'True',
        u'xsrf_token': xsrf_token})

    request = urllib_request.Request(codereview_url)

    # Add header: Authorization: OAuth <codereview access token>
    request.add_header(
        u'Authorization', u'OAuth {0:s}'.format(codereview_access_token))

    # This will change the request into a POST.
    request.add_data(post_data)

    try:
      url_object = urllib_request.urlopen(request)
    except urllib_error.HTTPError as exception:
      logging.error(
          u'Failed publish to codereview issue: {0!s} with error: {1!s}'.format(
              issue_number, exception))
      return False

    if url_object.code not in (200, 201):
      logging.error((
          u'Failed publish to codereview issue: {0!s} with status code: '
          u'{1:d}').format(issue_number, url_object.code))
      return False

    return True

  def CloseIssue(self, issue_number):
    """Closes a code review issue.

    Args:
      issue_number (int|str): codereview issue number.

    Returns:
      bool: True if the code review was closed.
    """
    codereview_access_token = self.GetAccessToken()
    xsrf_token = self.GetXSRFToken()
    if not codereview_access_token or not xsrf_token:
      return False

    codereview_url = b'https://codereview.appspot.com/{0!s}/close'.format(
        issue_number)

    post_data = urllib_parse.urlencode({u'xsrf_token': xsrf_token})

    request = urllib_request.Request(codereview_url)

    # Add header: Authorization: OAuth <codereview access token>
    request.add_header(
        u'Authorization', u'OAuth {0:s}'.format(codereview_access_token))

    # This will change the request into a POST.
    request.add_data(post_data)

    try:
      url_object = urllib_request.urlopen(request)
    except urllib_error.HTTPError as exception:
      logging.error(
          u'Failed closing codereview issue: {0!s} with error: {1!s}'.format(
              issue_number, exception))
      return False

    if url_object.code != 200:
      logging.error((
          u'Failed closing codereview issue: {0!s} with status code: '
          u'{1:d}').format(issue_number, url_object.code))
      return False

    return True

  def CreateIssue(self, project_name, diffbase, description):
    """Creates a new codereview issue.

    Args:
      project_name (str): name of the project.
      diffbase (str): diffbase.
      description (str): description.

    Returns:
      int: codereview issue number or None.
    """
    reviewer = self._GetReviewer(project_name)
    reviewers_cc = self._GetReviewersOnCC(project_name, reviewer)

    command = u'{0:s} {1:s} --oauth2'.format(
        sys.executable, self._upload_py_path)

    if self._no_browser:
      command = u'{0:s} --no_oauth2_webbrowser'.format(command)

    command = (
        u'{0:s} --send_mail -r {1:s} --cc {2:s} -t "{3:s}" -y -- '
        u'{4:s}').format(
            command, reviewer, reviewers_cc, description, diffbase)

    if self._no_browser:
      print(
          u'Upload server: codereview.appspot.com (change with -s/--server)\n'
          u'Go to the following link in your browser:\n'
          u'\n'
          u'    https://codereview.appspot.com/get-access-token\n'
          u'\n'
          u'and copy the access token.\n'
          u'\n')
      print(u'Enter access token:', end=u' ')

      sys.stdout.flush()

    exit_code, output, _ = self.RunCommand(command)
    print(output)

    if exit_code != 0:
      return

    issue_url_line_start = (
        u'Issue created. URL: http://codereview.appspot.com/')
    for line in output.split(b'\n'):
      if issue_url_line_start in line:
        _, _, issue_number = line.rpartition(issue_url_line_start)
        try:
          return int(issue_number, 10)
        except ValueError:
          pass

  def GetAccessToken(self):
    """Retrieves the OAuth access token.

    Returns:
      str: codereview access token.
    """
    if not self._access_token:
      # TODO: add support to get access token directly from user.
      self._access_token = upload_tool.GetAccessToken()
      if not self._access_token:
        logging.error(u'Unable to retrieve access token.')

    return self._access_token

  def GetXSRFToken(self):
    """Retrieves the XSRF token.

    Returns:
      str: codereview XSRF token or None if the token could not be obtained.
    """
    if not self._xsrf_token:
      codereview_access_token = self.GetAccessToken()
      if not codereview_access_token:
        return

      codereview_url = b'https://codereview.appspot.com/xsrf_token'

      request = urllib_request.Request(codereview_url)

      # Add header: Authorization: OAuth <codereview access token>
      request.add_header(
          u'Authorization', u'OAuth {0:s}'.format(codereview_access_token))
      request.add_header(u'X-Requesting-XSRF-Token', u'1')

      try:
        url_object = urllib_request.urlopen(request)
      except urllib_error.HTTPError as exception:
        logging.error(
            u'Failed retrieving codereview XSRF token with error: {0!s}'.format(
                exception))
        return

      if url_object.code != 200:
        logging.error((
            u'Failed retrieving codereview XSRF token with status code: '
            u'{0:d}').format(url_object.code))
        return

      self._xsrf_token = url_object.read()

    return self._xsrf_token

  def QueryIssue(self, issue_number):
    """Queries the information of a code review issue.

    The query returns JSON data that contains:
    {
      "description":str,
      "cc":[str],
      "reviewers":[str],
      "owner_email":str,
      "private":bool,
      "base_url":str,
      "owner":str,
      "subject":str,
      "created":str,
      "patchsets":[int],
      "modified":str,
      "project":str,
      "closed":bool,
      "issue":int
    }

    Where the "created" and "modified" strings are formatted as:
    "YYYY-MM-DD hh:mm:ss.######"

    Args:
      issue_number (int|str): codereview issue number.

    Returns:
      dict[str,object]: JSON response or None.
    """
    codereview_url = b'https://codereview.appspot.com/api/{0!s}'.format(
        issue_number)

    request = urllib_request.Request(codereview_url)

    try:
      url_object = urllib_request.urlopen(request)
    except urllib_error.HTTPError as exception:
      logging.error(
          u'Failed querying codereview issue: {0!s} with error: {1!s}'.format(
              issue_number, exception))
      return

    if url_object.code != 200:
      logging.error((
          u'Failed querying codereview issue: {0!s} with status code: '
          u'{1:d}').format(issue_number, url_object.code))
      return

    response_data = url_object.read()
    return json.loads(response_data)

  def UpdateIssue(self, issue_number, diffbase, description):
    """Updates a code review issue.

    Args:
      issue_number (int|str): codereview issue number.
      diffbase (str): diffbase.
      description (str): description.

    Returns:
      bool: True if the code review was updated.
    """
    command = u'{0:s} {1:s} --oauth2'.format(
        sys.executable, self._upload_py_path)

    if self._no_browser:
      command = u'{0:s} --no_oauth2_webbrowser'.format(command)

    command = (u'{0:s} -i {1!s} -m "Code updated." -t "{2:s}" -y -- '
               u'{3:s}').format(command, issue_number, description, diffbase)

    if self._no_browser:
      print(
          u'Upload server: codereview.appspot.com (change with -s/--server)\n'
          u'Go to the following link in your browser:\n'
          u'\n'
          u'    https://codereview.appspot.com/get-access-token\n'
          u'\n'
          u'and copy the access token.\n'
          u'\n')
      print(u'Enter access token:', end=u' ')

      sys.stdout.flush()

    exit_code, output, _ = self.RunCommand(command)
    print(output)

    return exit_code == 0

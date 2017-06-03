# -*- coding: utf-8 -*-
"""Helper for interacting with GitHub."""

import json
import logging
import sys

# pylint: disable=import-error,no-name-in-module
if sys.version_info[0] < 3:
  import urllib2 as urllib_error
  import urllib2 as urllib_request
else:
  import urllib.error as urllib_error
  import urllib.request as urllib_request


class GitHubHelper(object):
  """Github helper."""

  def __init__(self, organization, project):
    """Initializes a github helper.

    Args:
      organization (str): github organization name.
      project (str): github project name.
    """
    super(GitHubHelper, self).__init__()
    self._organization = organization
    self._project = project

  def CreatePullRequest(
      self, access_token, codereview_issue_number, origin, description):
    """Creates a pull request.

    Args:
      access_token (str): github access token.
      codereview_issue_number (int|str): codereview issue number.
      origin (str): origin of the pull request, formatted as:
          "username:feature".
      description (str): description.

    Returns:
      bool: True if the pull request was created.
    """
    title = b'{0!s}: {1:s}'.format(codereview_issue_number, description)
    body = (
        b'[Code review: {0!s}: {1:s}]'
        b'(https://codereview.appspot.com/{0!s}/)').format(
            codereview_issue_number, description)

    post_data = (
        b'{{\n'
        b'  "title": "{0:s}",\n'
        b'  "body": "{1:s}",\n'
        b'  "head": "{2:s}",\n'
        b'  "base": "master"\n'
        b'}}\n').format(title, body, origin)

    github_url = (
        u'https://api.github.com/repos/{0:s}/{1:s}/pulls?'
        u'access_token={2:s}').format(
            self._organization, self._project, access_token)

    request = urllib_request.Request(github_url)

    # This will change the request into a POST.
    request.add_data(post_data)

    try:
      url_object = urllib_request.urlopen(request)
    except urllib_error.HTTPError as exception:
      logging.error(
          u'Failed creating pull request: {0!s} with error: {1!s}'.format(
              codereview_issue_number, exception))
      return False

    if url_object.code not in (200, 201):
      logging.error(
          u'Failed creating pull request: {0!s} with status code: {1:d}'.format(
              codereview_issue_number, url_object.code))
      return False

    return True

  def GetForkGitRepoUrl(self, username):
    """Retrieves the git repository URL of a fork.

    Args:
      username (str): github username of the fork.

    Returns:
      str: git repository URL or None.
    """
    return u'https://github.com/{0:s}/{1:s}.git'.format(username, self._project)

  def QueryUser(self, username):
    """Queries a github user.

    Args:
      username (str): github user name.

    Returns:
      dict[str,object]: JSON response or None.
    """
    github_url = b'https://api.github.com/users/{0:s}'.format(username)

    request = urllib_request.Request(github_url)

    try:
      url_object = urllib_request.urlopen(request)
    except urllib_error.HTTPError as exception:
      logging.error(
          u'Failed querying github user: {0:s} with error: {1!s}'.format(
              username, exception))
      return

    if url_object.code != 200:
      logging.error(
          u'Failed querying github user: {0:d} with status code: {1:d}'.format(
              username, url_object.code))
      return

    response_data = url_object.read()
    return json.loads(response_data)

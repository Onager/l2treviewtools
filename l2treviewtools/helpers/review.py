# -*- coding: utf-8 -*-
"""Helper for conducting code reviews."""

from __future__ import print_function

import os
import re
import subprocess
import sys

from l2treviewtools.helpers import git
from l2treviewtools.helpers import github
from l2treviewtools.helpers import project
from l2treviewtools.helpers import pylint
from l2treviewtools.helpers import readthedocs
from l2treviewtools.helpers import sphinxapi
from l2treviewtools.helpers import upload
from l2treviewtools.lib import netrcfile
from l2treviewtools.lib import reviewfile


class ReviewHelper(object):
  """Defines review helper functions."""

  _PROJECT_NAME_PREFIX_REGEX = re.compile(
      r'\[({0:s})\] '.format(u'|'.join(
          project.ProjectHelper.SUPPORTED_PROJECTS)))

  def __init__(
      self, command, github_origin, feature_branch, diffbase, all_files=False,
      no_browser=False, no_confirm=False):
    """Initializes a review helper.

    Args:
      command (str): user provided command, for example "create", "lint".
      github_origin (str): github origin.
      feature_branch (str): feature branch.
      diffbase (str): diffbase.
      all_files (Optional[bool]): True if the command should apply to all
          files. Currently this only affects the lint command.
      no_browser (Optional[bool]): True if the functionality to use the
          webbrowser to get the OAuth token should be disabled.
      no_confirm (Optional[bool]): True if the defaults should be applied
          without confirmation.
    """
    super(ReviewHelper, self).__init__()
    self._active_branch = None
    self._all_files = all_files
    self._codereview_helper = None
    self._command = command
    self._diffbase = diffbase
    self._feature_branch = feature_branch
    self._git_helper = None
    self._git_repo_url = None
    self._github_helper = None
    self._github_origin = github_origin
    self._fork_feature_branch = None
    self._fork_username = None
    self._merge_author = None
    self._merge_description = None
    self._no_browser = no_browser
    self._no_confirm = no_confirm
    self._project_helper = None
    self._project_name = None
    self._sphinxapidoc_helper = None

    if self._github_origin:
      self._fork_username, _, self._fork_feature_branch = (
          self._github_origin.partition(u':'))

  def CheckLocalGitState(self):
    """Checks the state of the local git repository.

    Returns:
      bool: True if the state of the local git repository is sane.
    """
    if self._command in (
        u'close', u'create', u'lint', u'lint-test', u'lint_test', u'update'):
      if not self._git_helper.CheckHasProjectUpstream():
        print(u'{0:s} aborted - missing project upstream.'.format(
            self._command.title()))
        print(u'Run: git remote add upstream {0:s}'.format(self._git_repo_url))
        return False

    elif self._command == u'merge':
      if not self._git_helper.CheckHasProjectOrigin():
        print(u'{0:s} aborted - missing project origin.'.format(
            self._command.title()))
        return False

    if self._command not in (
        u'lint', u'lint-test', u'lint_test', u'test', u'update-version',
        u'update_version'):
      if self._git_helper.CheckHasUncommittedChanges():
        print(u'{0:s} aborted - detected uncommitted changes.'.format(
            self._command.title()))
        print(u'Run: git commit')
        return False

    self._active_branch = self._git_helper.GetActiveBranch()
    if self._command in (u'create', u'update'):
      if self._active_branch == u'master':
        print(u'{0:s} aborted - active branch is master.'.format(
            self._command.title()))
        return False

    elif self._command == u'close':
      if self._feature_branch == u'master':
        print(u'{0:s} aborted - feature branch cannot be master.'.format(
            self._command.title()))
        return False

      if self._active_branch != u'master':
        self._git_helper.SwitchToMasterBranch()
        self._active_branch = u'master'

    return True

  def CheckRemoteGitState(self):
    """Checks the state of the remote git repository.

    Returns:
      bool: True if the state of the remote git repository is sane.
    """
    if self._command == u'close':
      if not self._git_helper.SynchronizeWithUpstream():
        print((
            u'{0:s} aborted - unable to synchronize with '
            u'upstream/master.').format(self._command.title()))
        return False

    elif self._command in (u'create', u'update'):
      if not self._git_helper.CheckSynchronizedWithUpstream():
        if not self._git_helper.SynchronizeWithUpstream():
          print((
              u'{0:s} aborted - unable to synchronize with '
              u'upstream/master.').format(self._command.title()))
          return False

        force_push = True
      else:
        force_push = False

      if not self._git_helper.PushToOrigin(
          self._active_branch, force=force_push):
        print(u'{0:s} aborted - unable to push updates to origin/{1:s}.'.format(
            self._command.title(), self._active_branch))
        return False

    elif self._command in (u'lint', u'lint-test', u'lint_test'):
      self._git_helper.CheckSynchronizedWithUpstream()

    elif self._command == u'merge':
      if not self._git_helper.SynchronizeWithOrigin():
        print((
            u'{0:s} aborted - unable to synchronize with '
            u'origin/master.').format(self._command.title()))
        return False

    return True

  def Close(self):
    """Closes a review.

    Returns:
      bool: True if the close was successful.
    """
    if not self._git_helper.CheckHasBranch(self._feature_branch):
      print(u'No such feature branch: {0:s}'.format(self._feature_branch))
    else:
      self._git_helper.RemoveFeatureBranch(self._feature_branch)

    review_file = reviewfile.ReviewFile(self._feature_branch)
    if not review_file.Exists():
      print(u'Review file missing for branch: {0:s}'.format(
          self._feature_branch))

    else:
      codereview_issue_number = review_file.GetCodeReviewIssueNumber()

      review_file.Remove()

      if codereview_issue_number:
        if not self._codereview_helper.CloseIssue(codereview_issue_number):
          print(u'Unable to close code review: {0!s}'.format(
              codereview_issue_number))
          print((
              u'Close it manually on: https://codereview.appspot.com/'
              u'{0!s}').format(codereview_issue_number))

    return True

  def Create(self):
    """Creates a review.

    Returns:
      bool: True if the create was successful.
    """
    review_file = reviewfile.ReviewFile(self._active_branch)
    if review_file.Exists():
      print(u'Review file already exists for branch: {0:s}'.format(
          self._active_branch))
      return False

    git_origin = self._git_helper.GetRemoteOrigin()
    if not git_origin.startswith(u'https://github.com/'):
      print(u'{0:s} aborted - unsupported git remote origin: {1:s}'.format(
          self._command.title(), git_origin))
      print(u'Make sure the git remote origin is hosted on github.com')
      return False

    git_origin, _, _ = git_origin[len(u'https://github.com/'):].rpartition(u'/')

    netrc_file = netrcfile.NetRCFile()
    github_access_token = netrc_file.GetGitHubAccessToken()
    if not github_access_token:
      print(u'{0:s} aborted - unable to determine github access token.'.format(
          self._command.title()))
      print(u'Make sure .netrc is configured with a github access token.')
      return False

    last_commit_message = self._git_helper.GetLastCommitMessage()
    print(u'Automatic generated description of code review:')
    print(last_commit_message)
    print(u'')

    if self._no_confirm:
      user_input = None
    else:
      print(u'Enter a description for the code review or hit enter to use the')
      print(u'automatic generated one:')
      user_input = sys.stdin.readline()
      user_input = user_input.strip()

    if not user_input:
      description = last_commit_message
    else:
      description = user_input

    # Prefix the description with the project name for code review to make it
    # easier to distinguish between projects.
    code_review_description = u'[{0:s}] {1:s}'.format(
        self._project_name, description)

    codereview_issue_number = self._codereview_helper.CreateIssue(
        self._project_name, self._diffbase, code_review_description)
    if not codereview_issue_number:
      print(u'{0:s} aborted - unable to create codereview issue.'.format(
          self._command.title()))
      return False

    if not os.path.isdir(u'.review'):
      os.mkdir(u'.review')

    review_file.Create(codereview_issue_number)

    create_github_origin = u'{0:s}:{1:s}'.format(
        git_origin, self._active_branch)
    if not self._github_helper.CreatePullRequest(
        github_access_token, codereview_issue_number, create_github_origin,
        description):
      print(u'Unable to create pull request.')

    return True

  def InitializeHelpers(self):
    """Initializes the helper.

    Returns:
      bool: True if the helper initialization was successful.
    """
    script_path = os.path.abspath(__file__)

    self._project_helper = project.ProjectHelper(script_path)

    self._project_name = self._project_helper.project_name
    if not self._project_name:
      print(u'{0:s} aborted - unable to determine project name.'.format(
          self._command.title()))
      return False

    self._git_repo_url = b'https://github.com/log2timeline/{0:s}.git'.format(
        self._project_name)

    self._git_helper = git.GitHelper(self._git_repo_url)

    self._github_helper = github.GitHubHelper(
        u'log2timeline', self._project_name)

    if self._command in (u'close', u'create', u'merge', u'update'):
      email_address = self._git_helper.GetEmailAddress()
      self._codereview_helper = upload.UploadHelper(
          email_address, no_browser=self._no_browser)

    if self._command == u'merge':
      self._sphinxapidoc_helper = sphinxapi.SphinxAPIDocHelper(
          self._project_name)
      # TODO: disable the version check for now since sphinx-apidoc 1.2.2
      # on Unbuntu 14.04 does not have the --version option. Re-enable when
      # sphinx-apidoc 1.2.3 or later is introduced.
      # if not self._sphinxapidoc_helper.CheckUpToDateVersion():
      #   print((
      #       u'{0:s} aborted - sphinx-apidoc verion 1.2.0 or later '
      #       u'required.').format(self._command.title()))
      #   return False

    return True

  def Lint(self):
    """Lints a review.

    Returns:
      bool: True if linting was successful.
    """
    if self._project_name == u'l2tdocs':
      return True

    if self._command not in (
        u'create', u'merge', u'lint', u'lint-test', u'lint_test', u'update'):
      return True

    pylint_helper = pylint.PylintHelper()
    if not pylint_helper.CheckUpToDateVersion():
      print(u'{0:s} aborted - pylint verion 1.5.0 or later required.'.format(
          self._command.title()))
      return False

    if self._all_files:
      diffbase = None
    elif self._command == u'merge':
      diffbase = u'origin/master'
    else:
      diffbase = self._diffbase

    changed_python_files = self._git_helper.GetChangedPythonFiles(
        diffbase=diffbase)

    if not pylint_helper.CheckFiles(changed_python_files):
      print(u'{0:s} aborted - unable to pass linter.'.format(
          self._command.title()))

      if self._command == u'merge':
        self._git_helper.DropUncommittedChanges()
      return False

    return True

  def Merge(self, codereview_issue_number):
    """Merges a review.

    Args:
      codereview_issue_number (int|str): codereview issue number.

    Returns:
      bool: True if the merge was successful.
    """
    if not self._project_helper.UpdateVersionFile():
      print(u'Unable to update version file.')
      self._git_helper.DropUncommittedChanges()
      return False

    if not self._project_helper.UpdateDpkgChangelogFile():
      print(u'Unable to update dpkg changelog file.')
      self._git_helper.DropUncommittedChanges()
      return False

    apidoc_config_path = os.path.join(u'docs', u'conf.py')
    if os.path.exists(apidoc_config_path):
      self._sphinxapidoc_helper.UpdateAPIDocs()
      self._git_helper.AddPath(u'docs')

      readthedocs_helper = readthedocs.ReadTheDocsHelper(self._project_name)

      # The project wiki repo contains the documentation and
      # has no trigger on update webhook for readthedocs.
      # So we trigger readthedocs directly to build the docs.
      readthedocs_helper.TriggerBuild()

    if not self._git_helper.CommitToOriginInNameOf(
        codereview_issue_number, self._merge_author, self._merge_description):
      print(u'Unable to commit changes.')
      self._git_helper.DropUncommittedChanges()
      return False

    commit_message = (
        u'Changes have been merged with master branch. '
        u'To close the review and clean up the feature branch you can run: '
        u'python ./utils/review.py close {0:s}').format(
            self._fork_feature_branch)
    self._codereview_helper.AddMergeMessage(
        codereview_issue_number, commit_message)

    return True

  def Open(self, codereview_issue_number):
    """Opens a review.

    Args:
      codereview_issue_number (int|str): codereview issue number.

    Returns:
      bool: True if the open was successful.
    """
    # TODO: implement.
    # * check if feature branch exists
    # * check if review file exists
    # * check if issue number corresponds to branch by checking PR?
    # * create feature branch and pull changes from origin
    # * create review file
    _ = codereview_issue_number

    return False

  def PrepareMerge(self, codereview_issue_number):
    """Prepares a merge.

    Args:
      codereview_issue_number (int|str): codereview issue number.

    Returns:
      bool: True if the prepare were successful.
    """
    codereview_information = self._codereview_helper.QueryIssue(
        codereview_issue_number)
    if not codereview_information:
      print((
          u'{0:s} aborted - unable to retrieve code review: {1!s} '
          u'information.').format(
              self._command.title(), codereview_issue_number))
      return False

    self._merge_description = codereview_information.get(u'subject', None)
    if not self._merge_description:
      print((
          u'{0:s} aborted - unable to determine description of code review: '
          u'{1!s}.').format(
              self._command.title(), codereview_issue_number))
      return False

    # When merging remove the project name ("[project]") prefix from
    # the code review description.
    self._merge_description = self._PROJECT_NAME_PREFIX_REGEX.sub(
        u'', self._merge_description)

    merge_email_address = codereview_information.get(u'owner_email', None)
    if not merge_email_address:
      print((
          u'{0:s} aborted - unable to determine email address of owner of '
          u'code review: {1!s}.').format(
              self._command.title(), codereview_issue_number))
      return False

    github_user_information = self._github_helper.QueryUser(
        self._fork_username)
    if not github_user_information:
      print((
          u'{0:s} aborted - unable to retrieve github user: {1:s} '
          u'information.').format(
              self._command.title(), self._fork_username))
      return False

    merge_fullname = github_user_information.get(u'name', None)
    if not merge_fullname:
      merge_fullname = codereview_information.get(u'owner', None)
    if not merge_fullname:
      merge_fullname = github_user_information.get(u'company', None)
    if not merge_fullname:
      print((
          u'{0:s} aborted - unable to determine full name.').format(
              self._command.title()))
      return False

    self._merge_author = u'{0:s} <{1:s}>'.format(
        merge_fullname, merge_email_address)

    return True

  def PullChangesFromFork(self):
    """Pulls changes from a feature branch on a fork.

    Returns:
      bool: True if the pull was successful.
    """
    fork_git_repo_url = self._github_helper.GetForkGitRepoUrl(
        self._fork_username)

    if not self._git_helper.PullFromFork(
        fork_git_repo_url, self._fork_feature_branch):
      print(u'{0:s} aborted - unable to pull changes from fork.'.format(
          self._command.title()))
      return False

    return True

  def Test(self):
    """Tests a review.

    Returns:
      bool: True if the tests were successful.
    """
    if self._project_name == u'l2tdocs':
      return True

    if self._command not in (
        u'create', u'lint-test', u'lint_test', u'merge', u'test', u'update'):
      return True

    # TODO: determine why this alters the behavior of argparse.
    # Currently affects this script being used in plaso.
    command = u'{0:s} run_tests.py'.format(sys.executable)
    exit_code = subprocess.call(command, shell=True)
    if exit_code != 0:
      print(u'{0:s} aborted - unable to pass tests.'.format(
          self._command.title()))

      if self._command == u'merge':
        self._git_helper.DropUncommittedChanges()
      return False

    return True

  def Update(self):
    """Updates a review.

    Returns:
      bool: True if the update was successful.
    """
    review_file = reviewfile.ReviewFile(self._active_branch)
    if not review_file.Exists():
      print(u'Review file missing for branch: {0:s}'.format(
          self._active_branch))
      return False

    codereview_issue_number = review_file.GetCodeReviewIssueNumber()

    last_commit_message = self._git_helper.GetLastCommitMessage()
    print(u'Automatic generated description of the update:')
    print(last_commit_message)
    print(u'')

    if self._no_confirm:
      user_input = None
    else:
      print(u'Enter a description for the update or hit enter to use the')
      print(u'automatic generated one:')
      user_input = sys.stdin.readline()
      user_input = user_input.strip()

    if not user_input:
      description = last_commit_message
    else:
      description = user_input

    if not self._codereview_helper.UpdateIssue(
        codereview_issue_number, self._diffbase, description):
      print(u'Unable to update code review: {0!s}'.format(
          codereview_issue_number))
      return False

    return True

  def UpdateAuthors(self):
    """Updates the authors.

    Returns:
      bool: True if the authors update was successful.
    """
    if self._project_name == u'l2tdocs':
      return True

    if not self._project_helper.UpdateAuthorsFile():
      print(u'Unable to update authors file.')
      return False

    return True

  def UpdateVersion(self):
    """Updates the version.

    Returns:
      bool: True if the version update was successful.
    """
    if self._project_name == u'l2tdocs':
      return True

    if not self._project_helper.UpdateVersionFile():
      print(u'Unable to update version file.')
      return False

    if not self._project_helper.UpdateDpkgChangelogFile():
      print(u'Unable to update dpkg changelog file.')
      return False

    return True

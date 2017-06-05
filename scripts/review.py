#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Script to manage code reviews."""

from __future__ import print_function

import argparse
import os
import sys

from l2treviewtools.helpers.review import ReviewHelper


def Main():
  """The main program function.

  Returns:
    bool: True if successful or False if not.
  """
  argument_parser = argparse.ArgumentParser(
      description=u'Script to manage code reviews.')

  # TODO: add option to directly pass code review issue number.

  # yapf: disable
  argument_parser.add_argument(
      u'--allfiles', u'--all-files', u'--all_files', dest=u'all_files',
      action=u'store_true', default=False, help=(
          u'Apply command to all files, currently only affects the lint '
          u'command.'))

  argument_parser.add_argument(
      u'--diffbase', dest=u'diffbase', action=u'store', type=str,
      metavar=u'DIFFBASE', default=u'upstream/master', help=(
          u'The diffbase the default is upstream/master. This options is used '
          u'to indicate to what "base" the code changes are relative to and '
          u'can be used to "chain" code reviews.'))

  argument_parser.add_argument(
      u'--nobrowser', u'--no-browser', u'--no_browser', dest=u'no_browser',
      action=u'store_true', default=False, help=(
          u'Disable the functionality to use the webbrowser to get the OAuth '
          u'token should be disabled.'))

  argument_parser.add_argument(
      u'--noconfirm', u'--no-confirm', u'--no_confirm', dest=u'no_confirm',
      action=u'store_true', default=False, help=(
          u'Do not ask for confirmation apply defaults.\n'
          u'WARNING: only use this when you are familiar with the defaults.'))

  argument_parser.add_argument(
      u'--offline', dest=u'offline', action=u'store_true', default=False, help=(
          u'The review script is running offline and any online check is '
          u'skipped.'))

  commands_parser = argument_parser.add_subparsers(dest=u'command')

  close_command_parser = commands_parser.add_parser(u'close')

  # TODO: add this to help output.
  close_command_parser.add_argument(
      u'branch', action=u'store', metavar=u'BRANCH', default=None,
      help=u'name of the corresponding feature branch.')

  commands_parser.add_parser(u'create')

  merge_command_parser = commands_parser.add_parser(u'merge')

  # TODO: add this to help output.
  merge_command_parser.add_argument(
      u'codereview_issue_number', action=u'store',
      metavar=u'CODEREVIEW_ISSUE_NUMBER', default=None,
      help=u'the codereview issue number to be merged.')

  # TODO: add this to help output.
  merge_command_parser.add_argument(
      u'github_origin', action=u'store',
      metavar=u'GITHUB_ORIGIN', default=None,
      help=u'the github origin to merged e.g. username:feature.')

  merge_edit_command_parser = commands_parser.add_parser(u'merge-edit')

  # TODO: add this to help output.
  merge_edit_command_parser.add_argument(
      u'github_origin', action=u'store',
      metavar=u'GITHUB_ORIGIN', default=None,
      help=u'the github origin to merged e.g. username:feature.')

  merge_edit_command_parser = commands_parser.add_parser(u'merge_edit')

  # TODO: add this to help output.
  merge_edit_command_parser.add_argument(
      u'github_origin', action=u'store',
      metavar=u'GITHUB_ORIGIN', default=None,
      help=u'the github origin to merged e.g. username:feature.')

  commands_parser.add_parser(u'lint')

  commands_parser.add_parser(u'lint-test')
  commands_parser.add_parser(u'lint_test')

  open_command_parser = commands_parser.add_parser(u'open')

  # TODO: add this to help output.
  open_command_parser.add_argument(
      u'codereview_issue_number', action=u'store',
      metavar=u'CODEREVIEW_ISSUE_NUMBER', default=None,
      help=u'the codereview issue number to be opened.')

  # TODO: add this to help output.
  open_command_parser.add_argument(
      u'branch', action=u'store', metavar=u'BRANCH', default=None,
      help=u'name of the corresponding feature branch.')
  # yapf: enable

  # TODO: add submit option?

  commands_parser.add_parser(u'test')

  # TODO: add dry-run option to run merge without commit.
  # useful to test pending CLs.

  commands_parser.add_parser(u'update')

  commands_parser.add_parser(u'update-authors')
  commands_parser.add_parser(u'update_authors')

  commands_parser.add_parser(u'update-version')
  commands_parser.add_parser(u'update_version')

  options = argument_parser.parse_args()

  codereview_issue_number = None
  feature_branch = None
  github_origin = None

  print_help_on_error = False
  if options.command in (u'close', u'open'):
    feature_branch = getattr(options, u'branch', None)
    if not feature_branch:
      print(u'Feature branch value is missing.')
      print_help_on_error = True

      # Support "username:branch" notation.
      if u':' in feature_branch:
        _, _, feature_branch = feature_branch.rpartition(u':')

  if options.command in (u'merge', u'open'):
    codereview_issue_number = getattr(options, u'codereview_issue_number', None)
    if not codereview_issue_number:
      print(u'Codereview issue number value is missing.')
      print_help_on_error = True

  if options.command in (u'merge', u'merge-edit', u'merge_edit'):
    github_origin = getattr(options, u'github_origin', None)
    if not github_origin:
      print(u'Github origin value is missing.')
      print_help_on_error = True

  # yapf: disable
  if options.offline and options.command not in (
      u'lint', u'lint-test', u'lint_test', u'test'):
    print(u'Cannot run: {0:s} in offline mode.'.format(options.command))
    print_help_on_error = True
  # yapf: enable

  if print_help_on_error:
    print(u'')
    argument_parser.print_help()
    print(u'')
    return False

  home_path = os.path.expanduser(u'~')
  netrc_path = os.path.join(home_path, u'.netrc')
  if not os.path.exists(netrc_path):
    print(u'{0:s} aborted - unable to find .netrc.'.format(
        options.command.title()))  # yapf: disable
    return False

  review_helper = ReviewHelper(
      options.command,
      github_origin,
      feature_branch,
      options.diffbase,
      all_files=options.all_files,
      no_browser=options.no_browser,
      no_confirm=options.no_confirm)

  if not review_helper.InitializeHelpers():
    return False

  if not review_helper.CheckLocalGitState():
    return False

  if not options.offline and not review_helper.CheckRemoteGitState():
    return False

  if options.command == u'merge':
    if not review_helper.PrepareMerge(codereview_issue_number):
      return False

  if options.command in (u'merge', u'merge-edit', u'merge_edit'):
    if not review_helper.PullChangesFromFork():
      return False

  if not review_helper.Lint():
    return False

  if not review_helper.Test():
    return False

  result = False
  if options.command == u'create':
    result = review_helper.Create()

  elif options.command == u'close':
    result = review_helper.Close()

  elif options.command in (u'lint', u'lint-test', u'lint_test', u'test'):
    result = True

  elif options.command == u'merge':
    result = review_helper.Merge(codereview_issue_number)

  elif options.command == u'open':
    result = review_helper.Open(codereview_issue_number)

  elif options.command == u'update':
    result = review_helper.Update()

  elif options.command in (u'update-authors', u'update_authors'):
    result = review_helper.UpdateAuthors()

  elif options.command in (u'update-version', u'update_version'):
    result = review_helper.UpdateVersion()

  return result


if __name__ == u'__main__':
  if not Main():
    sys.exit(1)
  else:
    sys.exit(0)

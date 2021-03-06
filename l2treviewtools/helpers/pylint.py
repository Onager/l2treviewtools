# -*- coding: utf-8 -*-
"""Helper for interacting with pylint."""
from __future__ import print_function
import subprocess

from l2treviewtools.helpers import cli


class PylintHelper(cli.CLIHelper):
  """Pylint helper."""

  MINIMUM_VERSION = u'1.6.5'

  _MINIMUM_VERSION_TUPLE = MINIMUM_VERSION.split(u'.')

  def CheckFiles(self, filenames):
    """Checks if the linting of the files is correct using pylint.

    Args:
      filenames (list[str]): names of the files to lint.

    Returns:
      bool: True if the files were linted without errors.
    """
    print(u'Running linter on changed files.')
    failed_filenames = []
    for filename in filenames:
      print(u'Checking: {0:s}'.format(filename))

      command = u'pylint --rcfile=utils/pylintrc {0:s}'.format(filename)
      exit_code = subprocess.call(command, shell=True)
      if exit_code != 0:
        failed_filenames.append(filename)

    if failed_filenames:
      print(u'\nFiles with linter errors:')
      for failed_filename in filenames:
        print(u'\t{0:s}'.format(failed_filename))
      return False

    return True

  def CheckUpToDateVersion(self):
    """Checks if the pylint version is up to date.

    Returns:
      bool: True if the pylint version is up to date.
    """
    exit_code, output, _ = self.RunCommand(u'pylint --version')
    if exit_code != 0:
      return False

    version_tuple = (0, 0, 0)
    for line in output.split(b'\n'):
      if line.startswith(b'pylint '):
        _, _, version = line.partition(b' ')
        # Remove a trailing comma.
        version, _, _ = version.partition(b',')

        version_tuple = tuple([int(digit) for digit in version.split(b'.')])

    return version_tuple >= self._MINIMUM_VERSION_TUPLE

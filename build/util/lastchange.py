#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
lastchange.py -- Chromium revision fetching utility.
"""

import re
import logging
import optparse
import os
import subprocess
import sys

class VersionInfo(object):
  def __init__(self, revision_id, full_revision_string):
    self.revision_id = revision_id
    self.revision = full_revision_string


def RunGitCommand(directory, command):
  """
  Launches git subcommand.

  Errors are swallowed.

  Returns:
    A process object or None.
  """
  command = ['git'] + command
  # Force shell usage under cygwin. This is a workaround for
  # mysterious loss of cwd while invoking cygwin's git.
  # We can't just pass shell=True to Popen, as under win32 this will
  # cause CMD to be used, while we explicitly want a cygwin shell.
  if sys.platform == 'cygwin':
    command = ['sh', '-c', ' '.join(command)]
  try:
    proc = subprocess.Popen(command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=directory,
                            shell=(sys.platform=='win32'))
    return proc
  except OSError as e:
    logging.error('Command %r failed: %s' % (' '.join(command), e))
    return None


def FetchGitRevision(directory, filter):
  """
  Fetch the Git hash (and Cr-Commit-Position if any) for a given directory.

  Errors are swallowed.

  Returns:
    A VersionInfo object or None on error.
  """
  hsh = ''
  git_args = ['log', '-1', '--format=%H']
  if filter is not None:
    git_args.append('--grep=' + filter)
  proc = RunGitCommand(directory, git_args)
  if proc:
    output = proc.communicate()[0].strip()
    if proc.returncode == 0 and output:
      hsh = output
    else:
      logging.error('Git error: rc=%d, output=%r' %
                    (proc.returncode, output))
  if not hsh:
    return None
  pos = ''
  proc = RunGitCommand(directory, ['cat-file', 'commit', hsh])
  if proc:
    output = proc.communicate()[0]
    if proc.returncode == 0 and output:
      for line in reversed(output.splitlines()):
        if line.startswith('Cr-Commit-Position:'):
          pos = line.rsplit()[-1].strip()
          break
  return VersionInfo(hsh, '%s-%s' % (hsh, pos))


def FetchVersionInfo(directory=None, filter=None, out_file=None, version_macro=None):
  """
  Returns the last change (as a VersionInfo object)
  from some appropriate revision control system.
  """
  if out_file == 'src/build/util/LASTCHANGE':
    version_info = VersionInfo('a7c1b21614f6b5763bd597ab8fefd8678c073df9', 'a7c1b21614f6b5763bd597ab8fefd8678c073df9-refs/heads/master@{#764932}')
  elif version_macro is not None and version_macro == 'GPU_LISTS_VERSION':
    version_info = VersionInfo('6f4691ebdde8d27536a757ac13fd972e3b265ce4', '6f4691ebdde8d27536a757ac13fd972e3b265ce4-refs/branch-heads/3497@{#948}')
  elif version_macro is not None and version_macro == 'SKIA_COMMIT_HASH':
    version_info = VersionInfo('caab4546ccda874f74cb979eee680fbc2cc7e2e0', 'caab4546ccda874f74cb979eee680fbc2cc7e2e0-')
  else:
    version_info = FetchGitRevision(directory, filter)
  if not version_info:
    version_info = VersionInfo('0', '0')
  return version_info


def GetHeaderGuard(path):
  """
  Returns the header #define guard for the given file path.
  This treats everything after the last instance of "src/" as being a
  relevant part of the guard. If there is no "src/", then the entire path
  is used.
  """
  src_index = path.rfind('src/')
  if src_index != -1:
    guard = path[src_index + 4:]
  else:
    guard = path
  guard = guard.upper()
  return guard.replace('/', '_').replace('.', '_').replace('\\', '_') + '_'


def GetHeaderContents(path, define, version):
  """
  Returns what the contents of the header file should be that indicate the given
  revision.
  """
  header_guard = GetHeaderGuard(path)

  header_contents = """/* Generated by lastchange.py, do not edit.*/

#ifndef %(header_guard)s
#define %(header_guard)s

#define %(define)s "%(version)s"

#endif  // %(header_guard)s
"""
  header_contents = header_contents % { 'header_guard': header_guard,
                                        'define': define,
                                        'version': version }
  return header_contents


def WriteIfChanged(file_name, contents):
  """
  Writes the specified contents to the specified file_name
  iff the contents are different than the current contents.
  """
  try:
    old_contents = open(file_name, 'r').read()
  except EnvironmentError:
    pass
  else:
    if contents == old_contents:
      return
    os.unlink(file_name)
  open(file_name, 'w').write(contents)


def main(argv=None):
  if argv is None:
    argv = sys.argv

  parser = optparse.OptionParser(usage="lastchange.py [options]")
  parser.add_option("-m", "--version-macro",
                    help="Name of C #define when using --header. Defaults to " +
                    "LAST_CHANGE.",
                    default="LAST_CHANGE")
  parser.add_option("-o", "--output", metavar="FILE",
                    help="Write last change to FILE. " +
                    "Can be combined with --header to write both files.")
  parser.add_option("", "--header", metavar="FILE",
                    help="Write last change to FILE as a C/C++ header. " +
                    "Can be combined with --output to write both files.")
  parser.add_option("--revision-id-only", action='store_true',
                    help="Output the revision as a VCS revision ID only (in " +
                    "Git, a 40-character commit hash, excluding the " +
                    "Cr-Commit-Position).")
  parser.add_option("--print-only", action='store_true',
                    help="Just print the revision string. Overrides any " +
                    "file-output-related options.")
  parser.add_option("-s", "--source-dir", metavar="DIR",
                    help="Use repository in the given directory.")
  parser.add_option("", "--filter", metavar="REGEX",
                    help="Only use log entries where the commit message " +
                    "matches the supplied filter regex. Defaults to " +
                    "'^Change-Id:' to suppress local commits.",
                    default='^Change-Id:')
  opts, args = parser.parse_args(argv[1:])

  logging.basicConfig(level=logging.WARNING)

  out_file = opts.output
  header = opts.header
  filter=opts.filter

  while len(args) and out_file is None:
    if out_file is None:
      out_file = args.pop(0)
  if args:
    sys.stderr.write('Unexpected arguments: %r\n\n' % args)
    parser.print_help()
    sys.exit(2)

  if opts.source_dir:
    src_dir = opts.source_dir
  else:
    src_dir = os.path.dirname(os.path.abspath(__file__))

  version_info = FetchVersionInfo(directory=src_dir, filter=filter, out_file=out_file, version_macro=opts.version_macro)
  revision_string = version_info.revision
  if opts.revision_id_only:
    revision_string = version_info.revision_id

  if opts.print_only:
    print revision_string
  else:
    contents = "LASTCHANGE=%s\n" % revision_string
    if not out_file and not opts.header:
      sys.stdout.write(contents)
    else:
      if out_file:
        WriteIfChanged(out_file, contents)
      if header:
        WriteIfChanged(header,
                       GetHeaderContents(header, opts.version_macro,
                                         revision_string))

  return 0


if __name__ == '__main__':
  sys.exit(main())

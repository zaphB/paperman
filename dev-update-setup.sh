#!/usr/bin/env python3

import subprocess
import re
import sys
from os import path

cwd = path.dirname(__file__)

# run git update-index to find uncommitted changes
if subprocess.run('git update-index --refresh'.split(),
                  stdout=subprocess.DEVNULL,
                  stderr=subprocess.DEVNULL,
                  cwd=cwd).returncode not in (0, 1):
  raise RuntimeError('failed to run "git update-index"')

# as default, take latest release tag as version number and
# add the current commit tag as local tag
versionTags = (['v0.0.0']
              + list(filter(lambda t: re.match(r'v\d+\.\d+\.\d+', t),
                            subprocess.run('git tag --sort=committerdate'.split(),
                                           cwd=cwd,
                                           capture_output=True)
                                               .stdout.decode().split('\n'))))

commitHash = subprocess.run('git rev-parse --short HEAD'.split(),
                            capture_output=True,
                            cwd=cwd).stdout.decode().strip()

version = f'{versionTags[-1][1:]}+H{commitHash}'

# if current commit is tagged as release, set release version
if v := subprocess.run([*'git tag --points-at'.split(),
                        subprocess.run('git branch --show-current'.split(),
                                       capture_output=True,
                                       cwd=cwd).stdout.strip()],
                        capture_output=True,
                        cwd=cwd).stdout.decode():
  versionTags = list(filter(lambda t: re.match(r'v\d+\.\d+\.\d+', t),
                            v.split()))
  if len(versionTags) == 1:
    version = versionTags[0][1:]

# if uncommitted changes exist, add '-mod' to version
if subprocess.run('git diff-index --quiet HEAD --'.split(),
                  cwd=cwd).returncode != 0:
  version += ('+' if '+' not in version else '')+'mod'

# if --clean option is present, remove all version number extensions
if '--clean' in sys.argv:
  m = re.search(r'\d+\.\d+\.\d+', version)
  version = m.string[m.start():m.end()]

# replace in setup.py
result = []
replaceNextLine = False
for line in open('setup.py'):
  if replaceNextLine:
    result.append(f"version = '{version}'\n")
    replaceNextLine = False
  else:
    result.append(line)

  if line.strip().startswith('# DO NOT CHANGE'):
    replaceNextLine = True
open('setup.py', 'w').write(''.join(result))

# print version to stdout
print(version)

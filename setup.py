#!/usr/bin/python3

from setuptools import setup
import subprocess
import re
from os import path

cwd = path.dirname(__file__)

# read the contents of your README file
with open(path.join(cwd, 'README.md'),
          encoding='utf-8') as f:
  description = f.read()

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

version = f'{versionTags[-1][1:]}+c{commitHash}'

# if uncommitted changes exist, add '-modified' to version
if subprocess.run('git diff-index --quiet HEAD --'.split(),
                  cwd=cwd).returncode != 0:
  version += 'mod'


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


setup(name='paperman',
      description='latex project and bibliography management utility',
      long_description=description,
      long_description_content_type='text/markdown',
      author='zaphB',
      version=version,
      packages=['paperman'],
      entry_points={
        'console_scripts': [
          'paperman = paperman.__main__:main'
        ],
        'gui_scripts': []
      },
      install_requires=['appdirs']
)

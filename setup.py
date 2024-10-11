#!/usr/bin/python3

from setuptools import setup
from setuptools.command.install import install

# DO NOT CHANGE: this line will be replaced by ./dev/update-setup.py
version = '1.0.8'

# if setup is run in project dir, update version number
try:
  import os
  import subprocess
  p = os.path.join(os.path.dirname(__file__), 'dev/update-setup.sh')
  if (os.path.isfile(p) and os.access(p, os.X_OK)):
    version = subprocess.run([p], capture_output=True, check=True).stdout.decode().strip()
except KeyboardInterrupt:
  raise
except:
  pass

# prepare post-install command
class PostInstall(install):
  def run(self):
    install.run(self)
    import subprocess
    subprocess.run(['activate-global-python-argcomplete']) #, check=True)

# read the contents of your README file
from os import path
with open(path.join(path.dirname(__file__), 'README.md'),
          encoding='utf-8') as f:
  description = f.read()

# run setup
setup(name='paperman',
      description='latex project and bibliography management utility',
      python_requires='>=3.6',
      long_description=description,
      long_description_content_type='text/markdown',
      author='zaphB',
      version=version,
      packages=['paperman', 'paperman.subcommands', 'paperman.parser'],
      entry_points={
        'console_scripts': [
          'paperman = paperman.__main__:main'
        ],
        'gui_scripts': []
      },
      install_requires=['appdirs', 'argparse', 'argcomplete', 'pyyaml', 'cloudscraper', 'unidecode'],
      cmdclass={
        'install': PostInstall
      }
)

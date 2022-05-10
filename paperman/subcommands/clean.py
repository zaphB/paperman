import sys
import os
import subprocess
import re
import shutil
import time

from .common import *
from .. import cfg
from .. import io

p = lambda d: os.path.realpath(os.path.expanduser(d))
buildFilesTrash = p(cfg.get('clean', 'trash_folder'))
baseDirectory = p('.')
ignorePaths   = [p(d) for d in cfg.get('clean', 'ignore_paths')]
requiredSuffs = cfg.get('clean', 'required_suffs')
cleanSuffs = cfg.get('clean', 'clean_suffs')


def stripBaseDir(p):
  if p.startswith(baseDirectory):
    return p[len(baseDirectory):]
  return p


def main(args):
  m = []
  for root, dirs, files in os.walk(baseDirectory, topdown=True):
    i = 0
    while i < len(dirs):
      if dirs[i].startswith('.'):
        dirs.pop(i)
      else:
        i += 1
    if (all([any(['.'+rs in f for f in files]) for rs in requiredSuffs])
        and not any([root.startswith(ip) for ip in ignorePaths])):
      m.extend([f'{root}/{f}' for f in files
                        if any(['.'+cs in f for cs in cleanSuffs])])

  if len(m):
    io.info('found build files:', *m)
    if io.conf(f'move all found build files to {buildFilesTrash}?',
               default=False):
      for path in m:
        absPath, path = path, stripBaseDir(path)
        baseFolder = time.strftime('%Y-%m-%d')
        absMoveTo = os.path.realpath(f'{buildFilesTrash}/{baseFolder}/{path}')
        io.info(f'{stripBaseDir(absPath)} -> {stripBaseDir(absMoveTo)}')
        os.makedirs(os.path.dirname(absMoveTo), exist_ok=True)
        shutil.move(absPath, absMoveTo)
      io.info('all done.')
  else:
    io.info(f'no tex build files found in {baseDirectory}')

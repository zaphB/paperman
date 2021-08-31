import os

from . import common


class BibFile:
  def __init__(self, path):
    self.path = os.path.normpath(path)


  def exists(self):
    d = os.path.dirname(self.path) or '.'
    if not os.path.isdir(d):
      return False
    return any([common.filenamesEqual(os.path.basename(self.path), f)
                                                  for f in os.listdir(d)])

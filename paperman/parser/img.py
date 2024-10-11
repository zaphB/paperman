import os

from .. import io
from . import common


class ImgFile:
  def __init__(self, fname, paths=None):
    self.fname = fname
    self.paths = paths
    self.path = None
    if paths is None:
      self.path = os.path.normpath(fname)
    else:
      for p in list(paths)+['.']:
        _p = os.path.join(p, os.path.dirname(fname))
        if os.path.isdir(_p):
          for f in os.listdir(_p):
            if common.filenamesEqual(f, os.path.basename(fname)):
              self.path = os.path.join(p, f)
              break
          if self.path is not None:
            break

  def containsNewcommandArg(self):
    return common.containsNewcommandArg(self.fname)

  def __eq__(self, img):
    if self.path and img.path:
      return common.filenamesEqual(self.path, img.path)
    return common.filenamesEqual(os.path.basename(self.fname),
                                os.path.basename(img.fname))

  def __lt__(self, img):
    return self.path and img.path and self.path < img.path

  def __gt__(self, img):
    return self.path and img.path and self.path > img.path

  def exists(self):
    return self.path and os.path.exists(self.path)

  def __repr__(self):
    return f'img file: {self.path or self.fname}'

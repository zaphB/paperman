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
        for f in os.listdir(p):
          if self._filenamesEqual(f, fname):
            self.path = os.path.join(p, f)
            break
        if self.path is not None:
          break

  def _stripSuffix(self, n):
    res = n
    if '.' in n:
      i = n.rfind('.')
      if os.path.sep not in n[i:]:
        res = n[:i]
    return res


  def _filenamesEqual(self, n1, n2):
    return self._stripSuffix(n1) == self._stripSuffix(n2)


  def __eq__(self, img):
    return (self.path and img.path
            and self._filenamesEqual(self.path, img.path))


  def __lt__(self, img):
    return self.path and img.path and self.path < img.path


  def __gt__(self, img):
    return self.path and img.path and self.path > img.path


  def exists(self):
    return self.path and os.path.exists(self.path)


  def __repr__(self):
    return f'img file: {self.path or self.fname}'

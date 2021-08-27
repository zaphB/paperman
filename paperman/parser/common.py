import os

from .. import io


def pathRelTo(file, name):
  if type(file) is str:
    path = file
  elif hasattr(file, 'toplevel') and file.toplevel:
    return pathRelTo(file.toplevel, name)
  elif hasattr(file, 'path'):
    path = file.path
  return os.path.normpath(
             os.path.join(
                 os.path.dirname(path), name))

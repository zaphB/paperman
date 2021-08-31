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


def containsNewcommandArg(string):
  return '#' in string


def stripSuffix(n):
  res = n
  if '.' in n:
    i = n.rfind('.')
    if os.path.sep not in n[i:]:
      res = n[:i]
  return res


def filenamesEqual(n1, n2):
  return stripSuffix(n1) == stripSuffix(n2)

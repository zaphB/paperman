import os

from .. import io

_CACHE = {}


def cache(path, data):
  p = os.path.normpath(path)
  if p in _CACHE:
    io.dbg(f'loading fileinfo {p} from cache')
    data.update(_CACHE[p])
  else:
    io.dbg(f'creating new cache entry for {p}')
    _CACHE[p] = data


def pathRelTo(file, name):
  if type(file) is str:
    path = file
  elif hasattr(file, 'path'):
    path = file.path
  return os.path.normpath(
             os.path.join(
                 os.path.dirname(path), name))

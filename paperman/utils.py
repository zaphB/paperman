import time
import traceback
import os

from . import io
from . import cfg


def uniquePath(path):
  i = 0
  _path = path
  while os.path.exists(path):
    p = _path.split('.')
    if len(p) > 1:
      path = '.'.join(p[:-1])+f'-{i}.'+p[-1]
    i += 1
  return path


def logExceptionsAndRaise(func):
  def wrapper(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except KeyboardInterrupt:
      raise
    except:
      io.err(traceback.format_exc(), logOnly=True)
      raise
  return wrapper


def cacheReturnValue(func):
  def wrapper(*args, **kwargs):
    cacheAttr = '__cachedReturnValue__'
    if (not hasattr(func, cacheAttr)
         or getattr(func, cacheAttr) is None):
      setattr(func, cacheAttr, func(*args, **kwargs))
    return getattr(func, cacheAttr)
  return wrapper


def replaceSuffix(path, suff):
  suff = suff.strip()
  fname = os.path.basename(path)
  if '.' in fname:
    fname = '.'.join(fname.split('.')[:-1])
  if len(suff)>0 and not suff.startswith('.'):
    suff = '.'+suff
  return os.path.join(os.path.dirname(path), fname+suff)

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
  def wrapper(self, *args, **kwargs):
    cacheAttr = '_'+func.__name__
    if (not hasattr(self, cacheAttr)
         or getattr(self, cacheAttr) is None):
      setattr(self, cacheAttr, func(self, *args, **kwargs))
    return getattr(self, cacheAttr)
  return wrapper

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
    self = func
    if len(args) > 0:
      try:
        setattr(args[0], '__dummy_attribute_not_used_anywhere___', None)
        self = args[0]
        #io.dbg(f'cacheReturnValue decorator detected class '
        #       f'{self.__class__.__name__}')
      except:
        pass
    if self is func:
      pass
      #io.dbg(f'cacheReturnValue decorator detected function '
      #       f'{self.__name__}')
    cacheAttr = '_'+func.__name__
    if (not hasattr(self, cacheAttr)
         or getattr(self, cacheAttr) is None):
      setattr(self, cacheAttr, func(*args, **kwargs))
    return getattr(self, cacheAttr)
  return wrapper


def replaceSuffix(path, suff):
  suff = suff.strip()
  fname = os.path.basename(path)
  if '.' in fname:
    fname = '.'.join(fname.split('.')[:-1])
  if len(suff)>0 and not suff.startswith('.'):
    suff = '.'+suff
  return os.path.join(os.path.dirname(path), fname+suff)

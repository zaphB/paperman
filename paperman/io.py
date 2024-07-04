import logging
import logging.handlers as handlers
import os
import traceback
import appdirs
from numpy import log10

from . import cfg

_LOG_DIR             = appdirs.user_log_dir('paperman')
_LOGFILE_NAME        = 'paperman.log'
_ROTATE_DIR          = 'oldlogs'
_IS_INIT             = False

isVerbose            = False

def _logger():
  return logging.getLogger('paperman')


def _init():
  global _IS_INIT, _LOG_DIR
  if not type(_LOG_DIR) is str:
    _LOG_DIR = _LOG_DIR()
  os.makedirs(_LOG_DIR, exist_ok=True)
  for oldlog in [f for f in os.listdir(_LOG_DIR)
                    if f != _LOGFILE_NAME and f.startswith(_LOGFILE_NAME)]:
    os.makedirs(_LOG_DIR+'/'+_ROTATE_DIR, exist_ok=True)
    os.rename(_LOG_DIR+'/'+oldlog, _LOG_DIR+'/'+_ROTATE_DIR+'/'+oldlog)

  if not _IS_INIT:
    h = handlers.TimedRotatingFileHandler(_LOG_DIR+'/'+_LOGFILE_NAME, when='W6')
    h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
                                     datefmt='%d.%m. %I:%M:%S'))
    l = _logger()
    l.addHandler(h)
    if cfg.get('debug'):
      l.setLevel(logging.DEBUG)
    else:
      l.setLevel(logging.INFO)
    _IS_INIT = True


def setLogfile(name):
  global _IS_INIT, _LOGFILE_NAME
  name = str(name)
  if '/' in name:
    raise ValueError(f'logfile name must not contain a slash "/" : {name}')
  if not name.endswith('.log'):
    name += '.log'
  _logger().handlers.clear()
  _IS_INIT = False
  _LOGFILE_NAME = name
  _init()


def _indentMsg(msg):
  ls = [l for l in '\n'.join([str(l) for l in msg]).split('\n') if l.strip()]
  if len(ls) == 0:
    return ''
  if len(ls) == 1:
    return ls[0]
  elif len(ls) == 2:
    return ls[0]+'\n'+' '*2+r'\ '+ls[1]
  else:
    return ('\n'+' '*2+'| ').join(ls[:-1])+'\n'+' '*2+r'\ '+ls[-1]


def err(*msg, logOnly=False):
  _init()
  msg = _indentMsg(msg)
  _logger().error(msg)
  if not logOnly:
    print('error:', msg)
    if '\n' in msg:
      print()


def formatErr(*msg):
  return 'error: '+_indentMsg(msg)


def warn(*msg, logOnly=False):
  _init()
  msg = _indentMsg(msg)
  _logger().warning(msg)
  if not logOnly:
    print('warning:', msg)
    if '\n' in msg:
      print()


def info(*msg, logOnly=False, noNewLine=False):
  _init()
  msg = _indentMsg(msg)
  _logger().info(msg)
  if not logOnly:
    print(msg)
    if '\n' in msg and not noNewLine:
      print()


def raw(*msg):
  _init()
  _logger().info(_indentMsg(msg))
  print(*msg)


def verb(*msg, logOnly=False):
  if isVerbose:
    info(*msg, logOnly=logOnly)
  elif cfg.get('debug'):
    dbg(*msg, logOnly=logOnly)


def dbg(*msg, logOnly=False):
  _init()
  msg = _indentMsg(msg)
  _logger().debug(msg)
  if not logOnly and cfg.get('debug'):
    print('debug:', msg)
    if '\n' in msg:
      print()


def conf(*msg, default=None):
  _init()
  msg = _indentMsg(msg)
  if default is None:
    msg += ' (y/n)'
  elif default:
    msg += ' (Y/n)'
  else:
    msg += ' (y/N)'
  res = None
  while res is None:
    _logger().info(msg)
    print(msg, end=' ')
    i = input()
    _logger().info('user input: "'+str(i)+'"')
    if '\n' in msg:
      print()
    if i.strip() == '':
      res = default
    elif i.strip().lower() in ('y', 'yes'):
      res = True
    elif i.strip().lower() in ('n', 'no'):
      res = False
    if res is None:
      info('invalid input, expecting (y)es or (n)o\n')
  return res


def select(msg, options, default=None):
  _msg = (msg+'\n'
           +'\n'.join([
               f'{"" if default is None else ("default: " if i+1==default else " "*9)}'
               f'({i+1:{int(log10(len(options))+1)}d})'
               f' {str(o)}' for i, o in enumerate(options)]))
  res = None
  while res is None:
    info(_msg, noNewLine=True)
    i = input()
    _logger().info('user input: "'+str(i)+'"')
    if '\n' in _msg:
      print()
    if i.strip() == '':
      res = default
    else:
      try:
        res = int(i)
        if res < 1 or res > len(options):
          raise ValueError('value out of range')
      except ValueError:
        res = None
    if res is None:
      info(f'invalid input, expecting number between 1 and {len(options)}\n')
  return res-1, options[res-1]


def startup():
  _init()
  msg = _indentMsg([f'starting paperman v{__version__}'])
  info('', logOnly=True)
  info('-'*len(msg), logOnly=True)
  info(msg, logOnly=True)
  if cfg.get('debug'):
    print('debug:', msg)


def coercedStacktrace(lines):
  excLines = traceback.format_exc().split('\n')
  if len(excLines) <= lines:
    return '\n'.join(excLines)
  else:
    return (f'skipped {len(excLines)-lines} stack trace lines...\n...\n'
            +'\n'.join(excLines[-lines:]))

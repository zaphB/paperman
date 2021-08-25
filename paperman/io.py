import logging
import logging.handlers as handlers
import os
import traceback
import appdirs

from . import cfg

_LOG_DIR             = appdirs.user_log_dir('paperman')
_LOGFILE_NAME        = 'paperman.log'
_ROTATE_DIR          = 'oldlogs'
_IS_INIT             = False


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
    raise RuntimeError(f'logfile name must not contain a slash "/" : {name}')
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
    return ls[0]+'\n'+' '*2+'\ '+ls[1]
  else:
    return ('\n'+' '*2+'| ').join(ls[:-1])+'\n'+' '*2+'\ '+ls[-1]


def err(*msg, logOnly=False):
  _init()
  msg = _indentMsg(msg)
  _logger().error(msg)
  if not logOnly:
    print('error:', msg)


def warn(*msg, logOnly=False):
  _init()
  msg = _indentMsg(msg)
  _logger().warning(msg)
  if not logOnly:
    print('warning:', msg)


def info(*msg, logOnly=False):
  _init()
  msg = _indentMsg(msg)
  _logger().info(msg)
  if not logOnly:
    print(msg)


def dbg(*msg, logOnly=False):
  _init()
  msg = _indentMsg(msg)
  _logger().debug(msg)
  if not logOnly and cfg.get('debug'):
    print('debug:', msg)


def startup():
  _init()
  msg = _indentMsg([f'starting papaerman v{__version__}'])
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

import os
import copy
import appdirs

from . import io

try:
  import yaml
except:
  pass

_DEFAULT_CFG = dict(
  debug = False,
  max_directory_depth = 5,
  graphics_extensions = ['jpg', 'pdf', 'png']
)

_REQUIRED_CFG = dict()

_CFG_PATH = appdirs.user_config_dir('paperman')
_CFG = {}
_IS_CFG_LOADED = False
_HAS_TESTED_REQUIRED_KEYS = False


def _touchCfg():
  os.makedirs(os.path.dirname(_CFG_PATH), exist_ok=True)
  if not os.path.exists(_CFG_PATH):
    open(_CFG_PATH, 'w')


def _loadCfg():
  global _IS_CFG_LOADED, _CFG, _HAS_TESTED_REQUIRED_KEYS
  if not _IS_CFG_LOADED:
    _touchCfg()
    _CFG = yaml.safe_load(open(_CFG_PATH, 'r')) or {}
    _IS_CFG_LOADED = True
    _HAS_TESTED_REQUIRED_KEYS = False
    testIfRequiredExist()
    _writeCfg()


def _writeCfg():
  _touchCfg()
  yaml.dump({k: v for k, v in {**_DEFAULT_CFG, **_CFG}.items()},
            open(_CFG_PATH, 'w'))


def reload():
  global _IS_CFG_LOADED
  try:
    _IS_CFG_LOADED = False
    _loadCfg()
  except (KeyboardInterrupt, RuntimeError):
    raise
  except:
    io.err(io.coercedStacktrace(10))
    io.err('error reloading config file, reverting '
           'changes on disk')
    _writeCfg()
    _loadCfg()


def testIfRequiredExist(*path):
  global _HAS_TESTED_REQUIRED_KEYS, _IS_CFG_LOADED
  if not _HAS_TESTED_REQUIRED_KEYS:
    settings = _REQUIRED_CFG
    for p in path:
      settings = settings[p]
    if type(settings) is dict:
      for k in settings.keys():
        testIfRequiredExist(*path, k)
    else:
      if get(*path) is None:
        _IS_CFG_LOADED = False
        raise RuntimeError(f'config setting {".".join(path)} is required '
                           f'but is not set')
  if len(path) == 0:
    _HAS_TESTED_REQUIRED_KEYS = True


def get(*key):
  if len(key) < 1:
    raise ArgumentError('cfg.get() expects at least one argument: key')
  _loadCfg()
  setting, default = _CFG, _DEFAULT_CFG
  usedDefault = False
  for k in key:
    if k not in setting.keys():
      usedDefault = True
      setting[k] = default[k]
    default = default[k]
    setting = setting[k]

  if usedDefault:
    _writeCfg()

  return setting


def set(*keyVal):
  if len(keyVal) < 2:
    raise ArgumentError('cfg.set() expects at least two arguments: key and value')
  key = keyVal[:-1]
  val = nativify(keyVal[-1])
  reload()
  d = _CFG
  for k in key[:-1]:
    if k not in d:
      d[k] = {}
    d = d[k]
  d[key[-1]] = val
  _writeCfg()


def nativify(data, skipIfFunc=lambda data: False, skipIfError=False):
  args = dict(skipIfFunc=skipIfFunc, skipIfError=skipIfError)

  if data is None or type(data) in (bool, int, float, complex, str):
    return data

  if type(data) is dict:
    return {nativify(k, **args): nativify(v, **args) for k, v in data.items()}

  if hasattr(data, '__iter__'):
    try:
      return [nativify(v, **args) for v in data]
    except:
      pass

  try:
    return float(data)
  except:
    try:
      return complex(data)
    except:
      pass

  if skipIfError or skipIfFunc(data):
    return None

  raise ValueError('could not convert data to native type: "'+str(data)+'"')

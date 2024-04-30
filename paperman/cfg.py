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
  graphics_extensions = ['jpg', 'jpeg', 'pdf', 'png'],
  img_dir_name = 'img',
  img_search_paths = ['~/Documents'],
  img_search_priority = 'path-order, newest',
  input_search_paths = ['~/Documents'],
  input_search_priority = 'path-order, newest',
  bibtex_extensions = ['bib', 'bibtex'],
  bib_search_paths = ['~/Documents'],
  bib_search_priority = 'path-order, newest',
  bib_repair = dict(
    make_all_items_lowercase = True,
    merge_all_found_info = True,
    remove_fields = ['abstract'],
    generate_url_from_doi = True,
    repair_doi = True,
    verify_url_exists = True,
    verify_doi_exists = True,
    doi_and_url_verification_max_age_months = 1,
    force_double_hyphen_in_pages = True,
    keep_only_startpage_in_pages = False,
    convert_month_to_number = True,
    convert_journal_to_iso4_abbr = True,
    convert_journal_to_full_name = False,
    protect_capitalization_if_unprotected = True
  ),
  clean=dict(
    trash_folder = '~/Desktop/paperman-trash',
    ignore_paths = [],
    required_suffs = ['tex', 'pdf', 'aux'],
    clean_suffs = ['aux', 'bcf', 'log', 'snm', 'vrb', 'run.xml', 'synctex',
                   'nav', 'blg', 'fls', 'fdb_latexmk', 'toc', 'tdo', 'out']
  ),
  lint=dict(
    avoid_commands_in_toplevel=[],
    avoid_commands = [],
    avoid_words=[],
    known_authors=[],
#    check_spelling=[]
  ),
  library_path = '~/Documents/bibliography',
  library_sync_additional_paths = [],
  library_collect_paths = ['~/Desktop', '~/Downloads'],
  library_folder_pattern = '%Y-%m',
  library_sync_device = '',
  library_sync_max_age = 365*24*60*60,
  z_bib_words_protect_capitalization = [],
  z_bib_words_dont_protect_capitalization = [],
  z_bib_journals = {},
  z_verified_urls = [],
  z_verified_dois = []
)

_REQUIRED_CFG = dict()

_CFG_PATH = os.path.join(appdirs.user_config_dir('paperman'), 'paperman.conf')
_CFG = {}
_IS_CFG_LOADED = False
_HAS_TESTED_REQUIRED_KEYS = False


def _touchCfg():
  os.makedirs(os.path.dirname(_CFG_PATH), exist_ok=True)
  if not os.path.exists(_CFG_PATH):
    with open(_CFG_PATH, 'w') as f:
      pass


def _loadCfg():
  global _IS_CFG_LOADED, _CFG, _HAS_TESTED_REQUIRED_KEYS
  if not _IS_CFG_LOADED:
    _touchCfg()
    with open(_CFG_PATH, 'r') as f:
      _CFG = yaml.safe_load(f) or {}
    _IS_CFG_LOADED = True
    _HAS_TESTED_REQUIRED_KEYS = False
    testIfRequiredExist()
    _writeCfg()


def _writeCfg():
  _touchCfg()
  with open(_CFG_PATH, 'w') as f:
    yaml.dump({k: v for k, v in {**_DEFAULT_CFG, **_CFG}.items()}, f)


def path():
  return os.path.abspath(_CFG_PATH)


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

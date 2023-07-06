import shutil
import os
import fnmatch

from . import io
from . import cfg
from . import parser


def _candidateSortKey(rules):
  def key(c, rules=rules):
    pathNo, path = c[:2]
    res = ''
    for r in rules:
      if 'path-order' in r:
        res += f'_{pathNo:04d}'
      elif 'newest' in r:
        res += f'_{2**64-os.path.getmtime(path)}'
      elif 'oldest' in r:
        res += f'_{os.path.getmtime(path)}'
      else:
        raise RuntimeError(f'unknown priority rule {r}')
    return res
  return key


def _fastGlob(path):
  # walk through filesystem sub tree described by path up to the first '*'
  basePath = path.split('*')[0]

  # remove any inner '../' and './' from match path, as they dont make sense there
  matchPath = path.replace('/../', '/').replace('/./', '/')

  res = []
  hasWarnedDepth = False
  io.dbg(f'calling _fastGlob("{path}"), walking through "{basePath}"')
  for root, dirs, files in os.walk(basePath, topdown=True):
    # abort tree is too deep
    if root.count(os.sep)-basePath.count(os.path.sep)-2 > cfg.get('max_directory_depth'):
      io.verb(f'skipping subfolders of {root}')
      if not hasWarnedDepth:
        hasWarnedDepth = True
        io.warn(f'reached max_directory_depth='
                f'{cfg.get("max_directory_depth")} when recursing '
                f'through the current directory, ignoring deeper '
                f'levels')
      dirs.clear()

    # do not recurse into links
    while True:
      i = [d for d in dirs if os.path.islink(d)]
      if not i:
        break
      io.dbg(f'skipped link {i[0]}')
      dirs.remove(i[0])


    # skip hidden directories (e.g. git)
    while True:
      i = [d for d in dirs if d.startswith('.')]
      if not i:
        break
      #io.dbg(f'skipped hidden directory {i[0]}')
      dirs.remove(i[0])

    # check if any file matches
    for f in files:
      fname = os.path.join(root, f)
      #io.dbg(f' checked filename {fname} for match with {matchPath}')
      if fnmatch.fnmatch(fname, matchPath):
        res.append(fname)
  return res


def importImgs(imgs, imgDir):
  success, failed = [], []

  # generate search paths
  searchPaths = []
  for p in cfg.get('img_search_paths'):
    # expand ~ in path
    p = os.path.expanduser(p)

    # append unedited path
    searchPaths.append(p)

    # if no **-globb pattern detected, add standard one and add to list
    if '*' not in p:
      searchPaths.append(os.path.join(p, '**', cfg.get('img_dir_name')))

  # iterate through requested images and try to import
  for img in imgs:
    candidates = []
    for i, p in enumerate(searchPaths):
      candidates.extend([(i, c) for c in _fastGlob(
                                        os.path.join(p, img.fname+'.*'))])

    # in case no candidate was found, add img to failed list and continue
    if not candidates:
      failed.append(img)
      continue

    # generate sorting function according to config
    rules = cfg.get('img_search_priority').split()
    sortedCandidates = sorted(candidates, key=_candidateSortKey(rules))
    io.dbg(f'first ten matching candidates sorted by {rules}:', sortedCandidates[:10])
    _, bestMatch = sortedCandidates[0]

    # copy best match to desired location
    os.makedirs(imgDir, exist_ok=True)
    shutil.copy(bestMatch, imgDir)
    io.verb(f'copying {bestMatch} -> {imgDir}')
    success.append(img)

  return success, failed


def importCites(cites):
  success, failed = [], []

  # generate search paths
  searchPaths = []
  for p in (list(cfg.get('bib_search_paths'))
            + [cfg.get('library_path')+'/**'] if cfg.get('library_path') else []):
    # expand ~ in path
    p = os.path.expanduser(p)

    # append unedited path
    searchPaths.append(p)

  # create huge list with all found bib paths
  allCites = []
  for i, p in enumerate(searchPaths):
    for ext in cfg.get('bibtex_extensions'):
      for f in _fastGlob(os.path.join(p, '*.'+ext)):
        try:
          _cites = parser.BibFile(f).cites()
        except RuntimeError as e:
          io.warn('error parsing bibtex file on search path:',
                  str(e),
                  'skipping...')
        else:
          for c in _cites:
            if c not in [c for _, _, c in allCites]:
              allCites.append([i, f, c])

  # iterate through requested images and try to import
  for cite in cites:
    candidates = [(i, f, c) for i, f, c in allCites if c == cite]

    # in case no candidate was found, add cite to failed list and continue
    if not candidates:
      failed.append(cite)
      continue

    # generate sorting function according to config
    rules = cfg.get('bib_search_priority').split()
    sortedCandidates = sorted(candidates, key=_candidateSortKey(rules))
    io.dbg(f'first ten matching candidates sorted by {rules}:', sortedCandidates[:10])
    _, _path, bestMatch = sortedCandidates[0]
    io.verb(f'best match for citation with key "{cite.key}"',
            f'found in file',
            f'{_path}')

    if cfg.get('bib_repair', 'merge_all_found_info'):
      if len(sortedCandidates) > 1:
        io.verb('merging with info from all other candidates...')
      for c in sortedCandidates[1:]:
        bestMatch[-1].insertNonexistingItems(c[-1])

    success.append(bestMatch)

  return success, failed


def importInclude(include):
  success, failed = [], []

  if not os.path.exists(include):
    # generate search paths
    searchPaths = [os.path.expanduser(p) for p in cfg.get('input_search_paths')]

    # try to import
    candidates = []
    for i, p in enumerate(searchPaths):
       candidates.extend([(i, c) for c in _fastGlob(
                                os.path.join(p, os.path.basename(include)))])

    # in case no candidate was found, add input to failed list and return
    if not candidates:
      failed.append(include)
      return False

    # generate sorting function according to config
    rules = cfg.get('input_search_priority').split()
    sortedCandidates = sorted(candidates, key=_candidateSortKey(rules))
    io.dbg(f'first ten matching candidates sorted by {rules}:',
           sortedCandidates[:10])
    _, bestMatch = sortedCandidates[0]

    # copy best match to desired location
    os.makedirs(os.path.dirname(include) or '.', exist_ok=True)
    shutil.copy(bestMatch, include)
    io.verb(f'copying {bestMatch} -> {include}')
    return True
  return False

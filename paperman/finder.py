import shutil
import glob
import os

from . import io
from . import cfg
from . import parser


def _candidateSortKey(rules):
  def key(c, rules=rules):
    pathNo, path = c[:2]
    res = ''
    for r in rules:
      if 'path-order' in r:
        res += f'{pathNo:04d}'
      elif 'newest' in r:
        res += f'{2**64-os.path.getmtime(path)}'
      elif 'oldest' in r:
        res += f'{os.path.getmtime(path)}'
      else:
        raise RuntimeError(f'unknown priority rule {r}')
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
      candidates.extend([(i, c) for c in glob.glob(os.path.join(p, img.fname+'.*'),
                                                                recursive=True)])

    # in case no candidate was found, add img to failed list and continue
    if not candidates:
      failed.append(img)
      continue

    # generate sorting function according to config
    rules = cfg.get('img_search_priority').split()
    _, bestMatch = sorted(candidates, key=_candidateSortKey(rules))[0]

    # copy best match to desired location
    shutil.copy(bestMatch, imgDir)
    io.dbg(f'copying {bestMatch} -> {imgDir}')
    success.append(img)

  return success, failed


def importCites(cites):
  success, failed = [], []

  # generate search paths
  searchPaths = []
  for p in cfg.get('bib_search_paths'):
    # expand ~ in path
    p = os.path.expanduser(p)

    # append unedited path
    searchPaths.append(p)

    # if no **-globb pattern detected, add standard one and add to list
    if '*' not in p:
      searchPaths.append(os.path.join(p, '**', cfg.get('bib_dir_name')))

  # iterate through requested images and try to import
  for cite in cites:
    candidates = []
    for i, p in enumerate(searchPaths):
      for ext in cfg.get('bibtex_extensions'):
        for f in glob.glob(os.path.join(p, '*.'+ext), recursive=True):
          try:
            _cites = parser.BibFile(f).cites()
          except RuntimeError as e:
            io.warn('error parsing bibtex file on search path:',
                    str(e),
                    'skipping...')
          else:
            candidates.extend([(i, f, c) for c in _cites if c == cite])

    # in case no candidate was found, add cite to failed list and continue
    if not candidates:
      failed.append(cite)
      continue

    # generate sorting function according to config
    rules = cfg.get('bib_search_priority').split()
    _, _, bestMatch = sorted(candidates, key=_candidateSortKey(rules))[0]
    success.append(bestMatch)

  return success, failed

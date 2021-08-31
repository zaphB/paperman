import shutil
import glob
import os

from . import io
from . import cfg


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
    def candidateSortKey(c, rules=rules):
      pathNo, path = c
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
    _, bestMatch = sorted(candidates, key=candidateSortKey)[0]

    # copy best match to desired location
    shutil.copy(bestMatch, imgDir)
    io.dbg(f'copying {bestMatch} -> {imgDir}')
    success.append(img)

  return success, failed

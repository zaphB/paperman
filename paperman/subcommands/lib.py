import subprocess

from .. import utils
from .. import parser
from . common import *


def main(args):
  # check of library path is set
  libraryPath = os.path.expanduser(cfg.get('library_path'))
  if not libraryPath:
    io.err('library_path is not set in config file')
    return

  # set flags that decide what to do
  fulltextSearch = args.find_fulltext
  if fulltextSearch:
    try:
      subprocess.run(['pdf2txt', '-h'], capture_output=True)
    except KeyboardInterrupt:
      raise
    except:
      io.err(f'"pdf2txt -h" failed but is required',
             'for fulltext search, is pdf2txt correctly',
             'installed on your path?')
      return
  search = args.find
  matches = []

  scan = not search and not fulltextSearch
  healthyCount = 0
  foundDuplicates = {}
  foundTrueDuplicates = {}
  unpairedFiles = []
  invalidBibFiles = []
  invalidPdfFiles = []

  # walk through library
  hasWarnedDepth = False
  for root, dirs, files in os.walk(libraryPath, topdown=True):
    # skip annotated folder
    if os.path.relpath(root, libraryPath).startswith('annotated'):
      continue

    # abort tree is too deep
    if root.count(os.sep)-libraryPath.count(os.sep)-2 > cfg.get('max_directory_depth'):
      io.verb(f'skipping subfolders of {root}')
      if not hasWarnedDepth:
        hasWarnedDepth = True
        io.warn(f'reached max_directory_depth='
                f'{cfg.get("max_directory_depth")} when recursing '
                f'library, ignoring deeper levels')
      dirs.clear()

    # skip git directories
    while True:
      i = [d for d in dirs if d.startswith('.git')]
      if not i:
        break
      dirs.remove(i[0])

    # loop through files in dir
    for f in files:
      path = os.path.join(root, f)
      if any([f.lower().endswith('.'+e) for e in cfg.get('bibtex_extensions')]):
        # if bibfile and search is enabled, check of matching
        if search:
          try:
            c = parser.BibFile(path).cites()[0]
          except Exception:
            io.verb(f'skipping invalid library entry {path}')
          else:
            if all([any([s.lower() in v.lower()
                                  for v in c.fields.values()])
                                      for s in search]):
              matches.append(path)

        # if scan is enabled, check if file is successfully parsed
        if scan:
          try:
            c = parser.BibFile(path).cites()[0]
          except Exception:
            invalidBibFiles.append(path)
          else:
            # add to duplicate keys dict
            if c.key not in foundDuplicates:
              foundDuplicates[c.key] = []
            foundDuplicates[c.key].append(path)

            # add to true duplicates dict
            if c.compareAuthorTitle() not in foundTrueDuplicates:
              foundTrueDuplicates[c.compareAuthorTitle()] = []
            foundTrueDuplicates[c.compareAuthorTitle()].append(path)

            if os.path.exists('.'.join(path.split('.')[:-1])+'.pdf'):
              healthyCount += 0.5
            else:
              unpairedFiles.append(path)

      elif f.lower().endswith('.pdf'):
        # if pdf file and fulltext search enabled, check if matching
        if fulltextSearch:
          txtPath = os.path.join(root, '.'+f[:-4]+'.txt')
          # generate txt file if not existing or older than pdf
          if (not os.path.exists(txtPath)
                or os.path.getmtime(txtPath) < os.path.getmtime(path)):
            cmd = ['pdf2txt', '-o', txtPath, path]
            io.verb('running '+' '.join(cmd))
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode:
              io.warn(f'pdf2txt failed with exitcode {r.returncode}:',
                      r.stdout.decode(), r.stderr.decode(), f'skipping library entry {path}')

          if not os.path.isfile(txtPath):
            io.warn(f'pdf2txt did not create text file',
                    f'skipping library entry {path}')
          else:
            with open(txtPath, 'r') as f:
              txt = f.read()
            if all([s.lower() in txt.lower() for s in fulltextSearch]):
              matches.append(path)

        # if scan is enabled, check if file looks valid
        if scan:
          try:
            with open(path, 'rb') as f:
              if not f.read(16).startswith(b'%PDF'):
                raise ValueError('not pdf')
          except KeyboardInterrupt:
            raise
          except:
            invalidPdfFiles.append(path)
          else:
            if any([os.path.exists('.'.join(path.split('.')[:-1])+'.'+e)
                                for e in cfg.get('bibtex_extensions')]):
              healthyCount += 0.5
            else:
              unpairedFiles.append(path)

  if search or fulltextSearch:
    if not matches:
      io.info('no matches')
    for m in sorted(matches):
      bibPath = None
      for ext in cfg.get('bibtex_extensions'):
        _bibPath = utils.replaceSuffix(m, ext)
        if os.path.exists(_bibPath):
          bibPath = _bibPath
          break
      if args.long:
        if bibPath:
          io.raw(parser.BibFile(bibPath).cites()[0].toString())
      elif args.key:
        if bibPath:
          io.info(parser.BibFile(bibPath).cites()[0].key)
      else:
        io.info(m)

  if scan:
    foundDuplicates = {k: v for k, v in foundDuplicates.items()
                                                    if len(v) > 1}
    duplCount = sum([len(v)-1 for v in foundDuplicates.values()])
    foundTrueDuplicates = {k: v for k, v in foundTrueDuplicates.items()
                                                    if len(v) > 1}
    trueDuplCount = sum([len(v)-1 for v in foundTrueDuplicates.values()])
    io.info(f'done scanning library in {libraryPath},',
            f'found {healthyCount} valid looking entries', '-',
            *([f'found {len(unpairedFiles)} unpaired files:']
              +[f'  {f[len(libraryPath)+1:]}' for f in unpairedFiles]+['-']
                        if unpairedFiles else []),

            *([f'found {duplCount} duplicate keys:']
              +['  '+'\n  '.join([_d[len(libraryPath)+1:] for _d in d])
                                      for d in foundDuplicates.values()]+['-']
                        if foundDuplicates else []),

            *([f'found {trueDuplCount} true duplicates (title and authors identical):']
              +['  '+'\n  '.join([_d[len(libraryPath)+1:] for _d in d])
                                      for d in foundTrueDuplicates.values()]+['-']
                        if foundTrueDuplicates else []),

            *([f'found {len(invalidBibFiles)} invalid bib files:']
              +[f'  {b[len(libraryPath)+1:]}' for b in invalidBibFiles]+['-']
                        if invalidBibFiles else []),

            *([f'found {len(invalidPdfFiles)} invalid pdf files:']
              +[f'  {p[len(libraryPath)+1:]}' for p in invalidPdfFiles]
                        if invalidPdfFiles else []))

    # offer removing duplicates
    if (trueDuplCount
        and io.conf(f'remove {trueDuplCount} true duplicates from library?',
                    default=False)):
      for paths in foundTrueDuplicates.values():
        for path in sorted(paths)[:-1]:
          dir, base = os.path.split(path)
          base = '.'.join(base.split('.')[:-1])
          for p in os.listdir(dir):
            if p.startswith(base):
              rem = os.path.join(dir, p)
              io.info(f'removing {rem}')
              os.remove(rem)

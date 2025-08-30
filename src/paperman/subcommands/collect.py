import re
import time
import shutil

from .. import parser
from . common import *


def main(args):
  # check of library path is set
  libraryPath = os.path.expanduser(cfg.get('library_path'))
  if not libraryPath:
    io.err('library_path is not set in config file')
    return

  # check if collect paths exist
  collectPaths = args.paths or cfg.get('library_collect_paths')
  if collectPaths:
    io.verb('colling bib-pdf pairs from the follwoing paths:', *collectPaths)
  else:
    io.err('no collect paths specified, either',
           'set "library_collect_paths" in the config or',
           'pass paths as argument to "paperman collect"')
    return

  # define routine to use for error reporting
  lastErrStr = ''
  def onError(file, *err):
    nonlocal lastErrStr
    errStr = io.formatErr(f'failed to collect "{file}":', *err)
    if lastErrStr.lower().strip() != errStr.lower().strip():
      if args.err_to_file:
        with open(os.path.join(os.path.dirname(file),
                               'paperman-collect-error.txt'), 'w') as f:
          f.write(errStr)
      io.err(f'failed to collect "{file}":', *err)
      lastErrStr = errStr

  # mainloop
  while True:
    try:
      t0 = time.time()
      for p in collectPaths:
        p = os.path.expanduser(p)

        pdfs = [os.path.join(p, f) for f in os.listdir(p)
                          if os.path.isfile(os.path.join(p, f))
                              and f.lower().endswith('.pdf')]

        bibs = [os.path.join(p, f) for f in os.listdir(p)
                          if os.path.isfile(os.path.join(p, f))
                              and any([f.lower().endswith(e)
                                  for e in list(cfg.get('bibtex_extensions'))
                                                  +['.ris']])]

        io.verb('in folder ', p,
                'found pdf candidates: ', *(pdfs or ['-none-']),
                'found bib candidates: ', *(bibs or ['-none-']))

        # if exactly one non-empty pdf and one bib file exist, trigger collect
        if len(pdfs) == 1 and len(bibs) == 1 and os.path.getsize(pdfs[0]) > 16 and os.path.getsize(bibs[0]) > 16:
          pdfPath = pdfs[0]
          bibPath = bibs[0]

          # load and parse bib file (retry five times in case bib file was not
          # completely written when it was initially discovered)
          cites = []
          for _ in range(5):
            try:
              if bibPath.lower().endswith('.ris'):
                r = parser.BibFile.fromRis('key', bibPath)
                io.dbg(r)
                cites = r.cites()
              else:
                cites = parser.BibFile(bibPath).cites()
              if len(cites) != 1:
                raise ValueError('invalid number of citations in bib file')
              break
            except Exception:
              time.sleep(.1)

          io.dbg('cites:', cites)
          if len(cites) == 1:
            cite = cites[0]

            # run pretty method to clean up fields and trigger potential reformatting questions
            cite.pretty()

            # generate key and filename from paper title
            cite.key = cite.makeKey()
            libraryDir = os.path.join(libraryPath,
                                      time.strftime(cfg.get('library_folder_pattern')))
            target = os.path.join(libraryDir, cite.key)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if not any([f.startswith(target)
                            for f in os.listdir(os.path.dirname(target))]):
              targetName = target+'.'+cfg.get('bibtex_extensions')[0]
              try:
                with open(targetName, 'w') as f:
                  f.write(cite.pretty()+'\n')
              except Exception:
                if os.path.exists(targetName):
                  os.remove(targetName)
                raise
              os.remove(bibPath)
              #io.info(f'moved "{bibPath}" -> "{target}.{cfg.get("bibtex_extensions")[0]}"')
              shutil.move(pdfPath, target+'.pdf')
              #io.info(f'moved "{pdfPath}" -> "{target}.pdf"')
              io.info(f'imported "{cite.key}"')

              # reset lastErr memory
              lastErrStr = ''
            else:
              onError(pdfPath, 'failed to move files to library, target',
                      '"'+target+'"', 'already exists')

          else:
            onError(pdfPath, f'found unexpected citation count ({len(cites)}) in bib file')

        # situation that naturally occurs, do not print error
        elif (len(pdfs)==1 and len(bibs)==0) or (len(pdfs)==0 and len(bibs)==1):
          pass

        elif len(pdfs) or len(bibs):
          onError(p, f'found {len(pdfs)} pdf candidates and {len(bibs)} bib',
                     f'need to have exactly one of each to collect')

      # if watch option is not set run mainloop only once
      if not args.watch:
        break

      # calculate sleep to not consume more than 1% of cpu-load, but also not
      # faster less than 0.1s or more than 5s
      sleepTime = min(5, max(.1, 1e2*(time.time()-t0)))
      io.verb(f'sleeping for {sleepTime:.1f}s')
      time.sleep(sleepTime)

    except KeyboardInterrupt:
      io.info('received ctrl+c interrupt, exiting...')
      break
    except:
      if not args.watch:
        raise
      io.err('unexpected error:', io.coercedStacktrace(30))
      time.sleep(5)

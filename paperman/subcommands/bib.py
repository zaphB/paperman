from .common import *

def main(args):
  if (proj := detectProj(args)) is None:
    return

  unused = proj.unusedCites()
  if unused:
    io.info('found unused citations:', *sorted(unused))
  else:
    io.info('no unused citations')

  missing = proj.missingCites()
  if missing:
    io.info('found missing citations:', *sorted(missing))
  elif getattr(args, 'import'):
    io.info('no missing citations, nothing to import')
  else:
    io.info('no missing citations')

  # prepare flags wether to import missing, sort and rewrite
  importMissing = False
  if getattr(args, 'import'):
    importMissing = True
  rewrite = args.rewrite or args.sort is not False
  sortKey = None
  if args.sort is False:
    pass
  elif args.sort == 'key' or args.sort is None:
    sortKey = lambda c: c.key
  elif args.sort == 'date':
    sortKey = lambda c: (c['year'] or '0000')+(c['month'] or '00')
  elif args.sort == 'author':
    sortKey = lambda c: c['author'] or ''
  else:
    raise RuntimeError(f'unknown sort order "{args.sort}"')

  if missing and importMissing:
    # check if bibliography search is configured
    if len(cfg.get('bib_search_paths')) == 0:
      io.err('no "bib_search_paths" configured to import citations from')
      return

    # if verbose, print all detected graphicspaths of toplevel tex files
    for t in proj.toplevel():
      if t.bibs():
        io.verb(f'detected bibliographies of toplevel tex file',
                f'{t.path}: '
                +', '.join([b.path for b in t.bibs()]))

      # find missing cites for current toplevel file
      _missing = t.missingCites()
      if _missing:

        # import finder module and import all missing citations
        from .. import finder
        success, failed = finder.importCites(_missing)

        # report results
        if success:
          if len(success) == 1:
            io.info(f'successfully found citation')
          else:
            io.info(f'successfully found {len(success)} citations')
        if failed:
          io.info(f'could not find the following citations:',
                  *[f'"{c.key}"' for c in failed])


        if len(t.bibs()) == 0:
          raise RuntimeError(f'failed to detect bibliography file for '
                             f'tex file "{t.path}"')
        elif len(t.bibs()) == 1:
          bib = t.bibs()[0]

        else:
          _, bib = io.select(f'found multiple bibliography files for tex file',
                             f'"{t.path}"',
                             f'please select one', options=t.bibs())

        io.info(f'appending found citations to "{bib.path}"')
        bib.addCites(success)

  # go trough all toplevel files and apply actions
  if rewrite and not importMissing:
    for t in proj.toplevel():
      for bib in t.bibs():
        newCites = bib.cites()
        if sortKey:
          newCites = sorted(newCites, key=sortKey)
        bib.setCites(newCites)

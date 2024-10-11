from .common import *

def main(args):
  proj = detectProj(args)
  if proj is None:
    return

  unused = proj.unusedCites()
  if unused:
    io.info('detected unused citations:', *sorted(unused))
  else:
    io.info('no unused citations')

  missing = proj.missingCites()
  if missing:
    io.info('detected missing citations:', *sorted(missing))
  elif getattr(args, 'import'):
    io.info('no missing citations, nothing to import')
  else:
    io.info('no missing citations')

  # prepare flags wether to import missing, sort and rewrite
  importMissing = False
  if getattr(args, 'import'):
    importMissing = True
  rewrite = args.rewrite or args.sort or args.clean
  sortKey = None
  if not args.sort:
    pass
  elif args.sort == 'key' or args.sort is None:
    sortKey = lambda c: c.key
  elif args.sort == 'date':
    sortKey = lambda c: (c['year'] or '0000')+(c['month'] or '00')
  elif args.sort == 'author':
    sortKey = lambda c: c['author'] or ''
  else:
    raise RuntimeError(f'unknown sort order "{args.sort}"')

  # check if print is present and raise error if combined with conflicting options
  showOnly = False
  if hasattr(args, 'print') and getattr(args, 'print'):
    if importMissing or rewrite or sortKey:
      raise RuntimeError('--print option cannot be combined with --import, '
                         '--sort or --rewrite options')
    showOnly = True

  if missing and (importMissing or showOnly):
    # check if bibliography search is configured
    if len(cfg.get('bib_search_paths')) == 0:
      io.err('no "bib_search_paths" configured to import citations from')
      return

    # if verbose, print all detected graphicspaths of toplevel tex files
    for t in proj.toplevel():
      if t.bibs():
        io.verb(f'detected bibliographies of toplevel tex file',
                f'{t.path}: '
                +', '.join([b.path or b.fname for b in t.bibs()]))

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

        existingBibs = [b for b in t.bibs() if b.exists()]
        if showOnly:
          prettyBib = '\n\n'.join(['']+[c.pretty() for c in success]+[''])
          if len(existingBibs) == 0:
            io.info(f'copy the following to the bib file of toplevel file',
                    f'"{t.path}"')
          elif len(existingBibs) == 1:
            io.info(f'copy the following to the bib file:',
                    f'"{existingBibs[0].path}"',
                    f'of toplevel file "{t.path}"')
          elif len(existingBibs) > 1:
            io.info(f'copy the following to one of the bib files:',
                    '\n'.join([f'  "{b.path}"' for b in existingBibs]),
                    f'of toplevel file "{t.path}"')
          io.raw('-'*60+prettyBib+'-'*60)
        else:
          if len(existingBibs) == 0 and len(t.bibs()) == 1:
            t.bibs()[0].create()
            existingBibs = t.bibs()

          if len(existingBibs) == 0:
            raise RuntimeError(f'failed to detect bibliography file for '
                               f'tex file "{t.path}"')
          elif len(existingBibs) == 1:
            bib = existingBibs[0]

          else:
            i, _ = io.select(f'found multiple bibliography files for tex file',
                               f'"{t.path}"',
                               f'please select one',
                               options=[b.path for b in existingBibs])
            bib = existingBibs[i]

          io.info(f'appending found citations to "{bib.path}"')
          bib.addCites(success)

  # go trough all toplevel files and apply actions
  if rewrite and not importMissing:
    io.info('rewriting bib file(s)...')
    for t in proj.toplevel():
      for bib in t.bibs():

        # create list of all existing cites to manipulate on
        newCites = bib.cites()

        # remove unused citations if requested
        if unused and args.clean:
          if io.conf(f'remove all unused entries from bib file {bib.path}?', default=True):
            newCites = [c for c in newCites if c not in unused]

        # apply sorting scheme if requested
        if sortKey:
          newCites = sorted(newCites, key=sortKey)

        # write new list of citations to disk
        bib.setCites(newCites)

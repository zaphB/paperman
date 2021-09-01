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

  if missing and getattr(args, 'import'):
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
          io.info(f'successfully found {len(success)} citations')
        if failed:
          io.info(f'could not find the following citations:',
                  *[i.fname for i in failed])
        io.info(f'copy the following into the bibliography file of',
                t.path)
        io.raw('\n\n'.join([c.pretty() for c in success])+'\n')

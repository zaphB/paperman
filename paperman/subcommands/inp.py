from .common import *

class IncludeMissing(RuntimeError):
  pass

def main(args):
  enableImport = hasattr(args, 'import') and getattr(args, 'import')

  # check if image search is configured
  if enableImport:
    if len(cfg.get('input_search_paths')) == 0:
      io.err(r'no "input_search_paths" configured to import \input{} files from')
      return

  try:
    if (proj := detectProj(args,
                           enableIncludeImport=enableImport,
                           raiseOnIncludeNotFound=IncludeMissing)) is None:
      return
    for t in proj.toplevel():
      t.recurseThroughIncludes()

  except IncludeMissing as e:
    if enableImport:
      io.err(r'failed to import \input{} file:',
             str(e))
    else:
      io.info(r'found missing \input{} file:',
              str(e))

  else:
    io.info(r'all \inputs{} exist')

from .common import *

def main(args):
  proj = detectProj(args)
  if proj is None:
    return

  allFine = True
  for l in proj.lint():
    #io.dbg(f'proj.lint yielded {l}')
    f, ln, msg = l
    io.info(f'in file {f}, line {ln}:', msg)
    allFine = False

  if allFine:
    io.info('all fine')

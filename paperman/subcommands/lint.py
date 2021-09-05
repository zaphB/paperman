from .common import *

def main(args):
  if (proj := detectProj(args)) is None:
    return

  allFine = True
  for f, ln, msg in proj.lint():
    io.info(f'in file {f}, line {ln}:', msg)
    allFine = False

  if allFine:
    io.info('all fine')

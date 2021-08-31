
from .common import *

def main(args):
  if (proj := detectProj(args)) is None:
    return

  io.dbg('bibs:', *[t.path+': '+str([b.exists() for b in t.bibs()]) for t in proj.toplevel()])

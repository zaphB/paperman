
from .common import *

def main(args):
  if (proj := detectProj(args)) is None:
    return

  io.dbg('citations:', proj.toplevel()[1].bibs()[0].citations()[0].__dict__)

  #for t in proj.toplevel():
  #  c = t.cites()
  #  io.dbg(f'{c=}')


  # proj.allCites()
  # proj.missingCites()
  # proj.unusedCites()

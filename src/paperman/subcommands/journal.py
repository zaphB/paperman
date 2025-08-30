from ..parser import journal
from .common import *

def main(args):
  if args.list_suspicious:
    journal.printSuspicious()
  else:
    m = journal.find(*args.name)
    if not m:
      io.info('no journals found')
    else:
      longestAbbr = max([len(_m[0]) for _m in m])
      for abbr, name in m:
        if args.full:
          io.info(name)
        elif args.abbreviated:
          io.info(abbr)
        else:
          abbr += '": '
          io.info(f'"{abbr:<{longestAbbr+3}}"{name}"')

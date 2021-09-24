import subprocess

from .common import *

def main(args):
  if args.open:
    subprocess.run(['vim', cfg.path()])
  else:
    io.info(cfg.path())

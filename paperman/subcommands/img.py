from .. import io
from .. import project

def main(args):
  proj = project.Project(args)
  unused = proj.unusedImgs()
  if unused:
    io.info('found unused image files:', *unused)
  else:
    io.info('no unused image files')

  missing = proj.missingImgs()
  if missing:
    io.info('found missing images:', *missing)
  else:
    io.info('no missing images')

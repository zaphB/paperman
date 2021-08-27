from .. import io
from .. import project

def main(args):
  proj = project.Project(args)
  unused = proj.unusedImgs()
  if unused:
    io.info('found unused image files:', *sorted(unused))
  else:
    io.info('no unused image files')

  missing = proj.missingImgs()
  if missing:
    io.info('found missing images:', *sorted(missing))
  else:
    io.info('no missing images')

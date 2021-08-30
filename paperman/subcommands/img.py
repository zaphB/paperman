import os

from .. import cfg
from .. import io
from .. import project


# return if a path looks like a valid image directory according
# to the configured image directory name
def isGoodImageDirectory(p):
  return (os.path.sep+cfg.get('img_dir_name')+os.path.sep
                        in os.path.sep+p+os.path.sep)


# return prettified directory paths: img -> ./img/, ../a/b -> ../a/b/
def prettyDirectory(p):
  if p.startswith('.') or p.startswith(os.path.sep):
    res = p
  else:
    res = '.'+os.path.sep+p
  if not res.endswith(os.path.sep):
    res += os.path.sep
  return res


# main entry point
def main(args):
  proj = project.Project(args)

  if len(proj.toplevel()) > 3:
    if len(proj.toplevel()) > 20:
      io.info('detected toplevel files: ', *sorted(proj.toplevel())[:20], '...')
    else:
      io.info('detected toplevel files: ', *sorted(proj.toplevel()))
    if not io.conf('detected more than three toplevel files '
                  f'({len(proj.toplevel())}), continue?', default=False):
      return

  unused = proj.unusedImgs()
  if unused:
    io.info('found unused image files:', *sorted(unused))
  else:
    io.info('no unused image files')

  missing = proj.missingImgs()
  if missing:
    io.info('found missing images:', *sorted(missing))
  elif getattr(args, 'import'):
    io.info('no missing images, nothing to import')
  else:
    io.info('no missing images')

  if missing and getattr(args, 'import'):
    # check if image search is configured
    if len(cfg.get('img_search_paths')) == 0:
      io.err('no "img_search_paths" configured to import images from')
      return

    # print error and exit in case not iamge directory was detected
    if len(proj.imgDirs()) == 0:
      io.err('failed to detect image directory for current project')
      return

    # if exactly one image directory was detected, use this directory
    elif len(proj.imgDirs()) == 1:
      targetDir = proj.imgDirs()[0]

    # if more than one image directory was detected, ask user to select one
    else:
      allDirs = proj.imgDirs()
      mostProbable = sorted([d for d in allDirs if isGoodImageDirectory(d)])
      remaining = [d for d in allDirs if d not in mostProbable]
      if len(mostProbable) == 1:
        default = 1
      else:
        default = None

      # ask user to select directory
      _, targetDir = io.select('found multiple image directory candidates for current '
                               'project, please select one:',
                               [prettyDirectory(o) for o in mostProbable+remaining],
                               default=default)

    # ask user to confirm if selected directory does not look like an img directory
    if not isGoodImageDirectory(targetDir):
      if not io.conf(f'the selected target folder\n"{prettyDirectory(targetDir)}"',
                     f'does not look like a good image\nfolder, a good image'
                     f'folder should be named',
                     f'"{cfg.get("img_dir_name")+os.path.sep}"',
                     f'use this target folder anyway? ',
                     default=False):
        return

    # import finder module and import all missing imgs
    from .. import finder
    success, failed = finder.importImgs(missing, targetDir)

    # report results
    if success:
      io.info(f'successfully found and imported {len(success)} images')
    if failed:
      io.info(f'cound not find the following images:',
              *[i.fname for i in failed])

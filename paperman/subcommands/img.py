from .common import *

p = lambda d: os.path.realpath(os.path.expanduser(d))
trashFolder = p(cfg.get('clean', 'trash_folder'))
baseDirectory = p('.')

def stripBaseDir(p):
  if p.startswith(baseDirectory):
    return p[len(baseDirectory):]
  return p


def main(args):
  proj = detectProj(args)
  if proj is None:
    return

  unused = proj.unusedIncludedImgs()
  if unused:
    io.info('detected unused image files:', *sorted(unused))
  else:
    io.info('no unused image files')

  if unused and args.clean:
    if io.conf('move all unused images to paperman trash?', default=True):
      for img in unused:
        absPath, path = img.path, stripBaseDir(img.path)
        baseFolder = time.strftime('%Y-%m-%d')
        absMoveTo = os.path.realpath(f'{trashFolder}/{baseFolder}/{path}')
        io.info(f'{stripBaseDir(absPath)} -> {stripBaseDir(absMoveTo)}')
        os.makedirs(os.path.dirname(absMoveTo), exist_ok=True)
        shutil.move(absPath, absMoveTo)
    io.info('all done.')

  missing = proj.missingIncludedImgs()
  if missing:
    io.info('detected missing images:', *sorted(missing))
  elif getattr(args, 'import'):
    io.info('no missing images, nothing to import')
  else:
    io.info('no missing images')

  if missing and getattr(args, 'import'):
    # check if image search is configured
    if len(cfg.get('img_search_paths')) == 0:
      io.err('no "img_search_paths" configured to import images from')
      return

    # if verbose, print all detected graphicspaths of toplevel tex files
    for t in proj.toplevel():
      io.verb(f'detected graphicspaths of toplevel tex file',
              f'{t.path}:',
              *[f'  {prettyDirectory(p)}' for p in t.graphicspath()])

    # print error and exit in case no iamge directory was detected
    if len(proj.commonImageDirs()) == 0:
      io.err(r'failed to detect image directory for current project,',
             r'a valid images directory has to be set with \graphicspath{}',
             r'in all toplevel tex documents of the project')
      return

    # if exactly one image directory was detected, use this directory
    elif len(proj.commonImageDirs()) == 1:
      targetDir = proj.commonImageDirs()[0]
      io.verb('found exactly one common graphicspath among all toplevel tex files:',
              targetDir)

    # if more than one image directory was detected, ask user to select one
    else:
      allDirs = proj.commonImageDirs()
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
      if len(success) == 1:
        io.info(f'successfully found and imported image')
      else:
        io.info(f'successfully found and imported {len(success)} images')
    if failed:
      io.info(f'could not find the following images:',
              *[i.fname for i in failed])

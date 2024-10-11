import os
import shutil
import time

from .. import project
from .. import cfg
from .. import io

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


# detect project from either given toplevel path of current directory
# warn and offer to cancel if too many toplevel files are detected
def detectProj(args, **kwargs):
  proj = project.Project(args, **kwargs)

  if len(proj.toplevel()) > 3:
    if len(proj.toplevel()) > 20:
      io.info('detected toplevel files: ', *sorted(proj.toplevel())[:20], '...')
    else:
      io.info('detected toplevel files: ', *sorted(proj.toplevel()))
    if not io.conf(f'detected {len(proj.toplevel())} toplevel files, continue?',
                   default=False):
      return None
  return proj

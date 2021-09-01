import os

from . import cfg
from . import io
from . import utils
from . import parser


class Project:
  def __init__(self, args):
    self.args = args
    self._warnings = []


  def _walk(self, find):
    # walk through directories and find specified stuff
    res = []

    # default to current directory only
    origins = ['.']

    # also walk through all found includedirs for graphics if
    # looking for images
    if find in ('imgs', ):
      for t in self.toplevel():
        for p in t.graphicspath():
          if p not in origins:
            origins.append(p)

    # walk through directories
    for o in origins:
      for root, dirs, files in os.walk(o, topdown=True):

        # abort tree is too deep
        if root.count(os.sep) > cfg.get('max_directory_depth'):
          io.warn(f'reached max_directory_depth='
                  f'{cfg.get("max_directory_depth")} when recursing '
                  f'through the current directory, ignoring deeper '
                  f'levels')
          break

        # skip git directories
        while i := [d for d in dirs if d.startswith('.git')]:
          dirs.remove(i[0])

        # find and open tex files to detect toplevel
        for f in files:
          if find in ('toplevel', ):
            if f.lower().endswith('.tex'):
              file = parser.TexFile(os.path.join(root, f))
              if file.isToplevel():
                res.append(file)

          if find in ('imgs', ):
            if (any([f.endswith('.'+(e[1:] if e.startswith('.') else e))
                                  for e in cfg.get('graphics_extensions')])
                # skip pdfs that seem to be builds of tex files
                and not (f.endswith('.pdf')
                          and os.path.exists(os.path.join(root, f[:-4]+'.tex')))):
              file = parser.ImgFile(os.path.join(root, f))
              if file not in res:
                res.append(file)
    return res


  @utils.cacheReturnValue
  def toplevel(self):
    if hasattr(self.args, 'tex_file') and self.args.tex_file:
      return [parser.TexFile(self.args.tex_file)]
    else:
      res = self._walk(find='toplevel')
      if res:
        io.verb(f'detected toplevel tex files:',
                *[str(t) for t in res])
      return res


  @utils.cacheReturnValue
  def commonImageDirs(self):
    res = [[p for p in t.graphicspath()] for t in self.toplevel()]
    res = [_p for p in res for _p in p if all([_p in p for p in res])]
    return sorted(list(set(res)))


  @utils.cacheReturnValue
  def allImgFiles(self):
      return sorted(self._walk(find='imgs'))


  @utils.cacheReturnValue
  def allIncludedImgs(self):
    res = []
    for t in self.toplevel():
      for i in t.imgs():
        if i not in res:
          res.append(i)
    return sorted(res)


  @utils.cacheReturnValue
  def unusedIncludedImgs(self):
    res = [f for f in self.allImgFiles()
              if any([f.path.startswith(d) for d in self.commonImageDirs()])]
    for i in self.allIncludedImgs():
      if i in res:
        res.remove(i)
    return sorted(res)


  @utils.cacheReturnValue
  def missingIncludedImgs(self):
    res = [f for f in self.allIncludedImgs()
                          if not f.exists()]
    valid = [f for f in res if not f.containsNewcommandArg()]
    if res != valid:
      w = (r'found \includegraphcis{} call with #n in argument, cannot '
           r'check if image exists for such calls')
      if w not in self._warnings:
        self._warnings.append(w)
      io.warn(w)
    return sorted(valid)
import os

from . import cfg
from . import io
from . import parser


class Project:
  def __init__(self, args):
    self.args = args
    self._toplevel = None
    self._imgFiles = None
    self._imgDirs = None
    self._includedImgs = None
    self._missingImgs = None
    self._unusedImgs = None
    self._warnings = []


  def _walk(self, find):
    # walk through directories and find toplevel tex files
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
            if (any([f.lower().endswith('.'+e.lower())
                        for e in cfg.get('graphics_extensions')])
                # skip pdfs that seem to be builds of tex files
                and not (f.lower().endswith('.pdf')
                          and os.path.exists(os.path.join(root, f[:-4]+'.tex')))):
              file = parser.ImgFile(os.path.join(root, f))
              if file not in res:
                res.append(file)
    return res


  def toplevel(self):
    if self._toplevel is None:
      if hasattr(self.args, 'tex_file') and self.args.tex_file:
        self._toplevel = [parser.TexFile(self.args.tex_file)]
      else:
        self._toplevel = self._walk(find='toplevel')
        if self._toplevel:
          io.verb(f'detected toplevel tex files:',
                  *[str(t) for t in self._toplevel])
    return self._toplevel


  def imgDirs(self):
    if self._imgDirs is None:
      res = [[p for p in t.graphicspath()] for t in self.toplevel()]
      res = [_p for p in res for _p in p if all([_p in p for p in res])]
      self._imgDirs = sorted(list(set(res)))
    return self._imgDirs


  def imgFiles(self):
    if self._imgFiles is None:
      self._imgFiles = sorted(self._walk(find='imgs'))
    return self._imgFiles


  def includedImgs(self):
    if self._includedImgs is None:
      res = []
      for t in self.toplevel():
        for i in t.imgs():
          if i not in res:
            res.append(i)
      self._includedImgs = sorted(res)
    return self._includedImgs


  def unusedImgs(self):
    if self._unusedImgs is None:
      res = [f for f in self.imgFiles()
                if any([f.path.startswith(d) for d in self.imgDirs()])]
      for i in self.includedImgs():
        if i in res:
          res.remove(i)

      self._unusedImgs = sorted(res)
    return res


  def missingImgs(self):
    if self._missingImgs is None:
      res = [f for f in self.includedImgs()
                            if not f.exists()]
      valid = [f for f in res if not f.containsNewcommandArg()]
      if res != valid:
        w = (r'found \includegraphcis{} call with #n in argument, cannot '
             r'check if image exists for such calls')
        if w not in self._warnings:
          self._warnings.append(w)
        io.warn(w)
      self._missingImgs = sorted(valid)
    return self._missingImgs

import re
import os

from .. import io
from . import common
from .img import ImgFile


class TexFile:
  def __init__(self, path, toplevel=None):
    if not os.path.exists(path):
      raise RuntimeError(f'file {path} does not exist')

    self.path = os.path.normpath(path)
    self.toplevel = toplevel
    self._content = None
    self._isToplevel = None
    self._includes = None
    self._graphicspath = None


  def __repr__(self):
    return f'tex file: {self.path}'


  def __eq__(self, file):
    return self.path and file.path and self.path == file.path


  def __lt__(self, file):
    return self.path and file.path and self.path < file.path


  def __gt__(self, file):
    return self.path and file.path and self.path > file.path


  def content(self):
    if self._content is None:
      self._content = '\n'.join([l for l in open(self.path, 'r')
                                    if not l.strip().startswith('%')])
    return self._content


  def includes(self):
    if self._includes is None:
      res = []
      for m in re.finditer(r'\\input(\[[^[\]]*\])?\{([^{}]+)\}', self.content()):
        fname = m.groups()[-1]
        if not fname.endswith('.tex'):
          fname += '.tex'
        res.append(TexFile(common.pathRelTo(self, fname),
                           toplevel=(self.toplevel or self)))
      self._includes = res
      if self._includes:
        io.verb(f'found include files of {self.path}: ',
                *[i.path for i in self._includes])
    return self._includes


  def isToplevel(self):
    if self._isToplevel is None:
      self._isToplevel = (all([re.search(s, self.content())
                              for s in (r'\\begin\{document\}',
                                        r'\\end\{document\}')])
                          and self.toplevel is None)
    return self._isToplevel


  def graphicspath(self, paths=[], latexlines=[]):
    if self._graphicspath is None:
      # function to call if \graphicspath call is encountered
      def detectedPaths(p):
        nonlocal paths
        if paths == []:
          paths = p
        elif paths != p:
          maxW = max([len(l[0]) for l in latexlines])
          raise RuntimeError(r'found conflicting \graphicspath{...} commands:'f'\n'
                             +'\n'.join([f'{p+":":<{maxW+1}} {l}'
                                              for p, l in latexlines]))

      # scan through include files
      for i in self.includes():
        detectedPaths(i.graphicspath(paths=paths, latexlines=latexlines))

      # scan self
      for m in re.finditer(r'.*\\graphicspath\{((\s*\{[^{}]+\}\s*)+)\}.*',
                           self.content()):
        latexlines.append([self.path, m.string[m.start():m.end()]])
        _p = [m.groups()[0] for m in re.finditer(r'\{([^{}]*)\}',
                                                    re.sub(r'\s+', '', m.groups()[0]))]
        detectedPaths([common.pathRelTo(self, p) for p in _p])

      for p in paths:
        if not os.path.isdir(p):
          io.dbg(f'found graphicspath {p}, which does not exist, ignoring')
      self._graphicspath = [p for p in paths if os.path.isdir(p)]
      if self._graphicspath:
        io.verb(f'found graphicspaths of {self.path}: '
                f'{", ".join(self._graphicspath)}')
    return self._graphicspath


  def imgs(self):
    res = []
    for i in self.includes():
      for file in i.imgs():
        if file not in res:
          res.append(file)
    for m in re.finditer(r'.*\\includegraphics(\[[^[\]]*\])?\{([^{}]+)\}.*', self.content()):
      file = ImgFile(m.groups()[-1], paths=self.graphicspath())
      if file not in res:
        res.append(file)
        if os.path.sep in file.fname:
          io.warn(r'found \includegraphics call with path instead of name:',
                  m.string[m.start():m.end()],
                  r'it is recommended to define image folders in the preample with',
                  r'\graphicspath{} and to use only names in \includegraphics '
                  f'calls, e.g.:',
                  f'\\graphicspath{{ ... {{{os.path.dirname(file.fname)+os.path.sep}}} ... }}'
                  f'and',
                  f'\\includegraphics[ ... ]{{{os.path.basename(file.fname)}}}')
    return res

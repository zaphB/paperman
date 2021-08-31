import re
import os

from .. import io
from . import common
from .img import ImgFile
from .bib import BibFile


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
    self._imgs = None
    self._bibHealthy = None
    self._bibs = None
    self._packageIncludes = None


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
    if self._imgs is None:
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
            io.warn(f'in file "{self.path}":',
                    m.string[m.start():m.end()],
                    r'it is recommended to define image folders in the preample with',
                    r'\graphicspath{} and to use only names in \includegraphics '
                    f'calls, e.g.:',
                    f'\\graphicspath{{ ... {{{os.path.dirname(file.fname)+os.path.sep}}} ... }}'
                    f'and',
                    f'\\includegraphics[ ... ]{{{os.path.basename(file.fname)}}}')
      self._imgs = res
    return self._imgs


  def bibs(self):
    if self._bibs is None:
      res = []
      if self.toplevel is None:
        self._packageIncludes = 0
      for i in self.includes():
        for b in i.bibs():
          if b not in res:
            res.append(b)

      # search for biblatex package loading
      for m in re.finditer(r'.*\\usepackage(\[[^[\]]*\])?{biblatex}.*',
                           self.content()):
        (self.toplevel or self)._packageIncludes += 1
        options = ''
        if len(m.groups()):
          options = m.groups()[0]
        if not (m := re.search(r'backend\s*=\s*biber', options)):
          io.warn(f'in file "{self.path}":',
                  f'{m.string[m.start():m.end()]}'
                  f'it is recommended to use biblatex with backend=biber option')

      # search for deprectaed natbib and warn
      for m in re.finditer(r'.*\\usepackage(\[[^[\]]*\])?{natbib}.*',
                           self.content()):
        (self.toplevel or self)._packageIncludes += 1
        io.warn(f'in file "{self.path}":',
                f'{m.string[m.start():m.end()]}',
                f'natbib pacakge is deprecated, it is recommended to use',
                f'the biblatex package with backend=biber instead')
        (self.toplevel or self)._bibHealthy = False

      # warn if more than one package loading match occured
      if self.toplevel is None and self._packageIncludes > 1:
        io.warn(f'bibliography package is included multiple times in file',
                f'{self.path}')

      # search for bibliography and addbibresource commands
      for s in ('addbibresource', 'bibliography'):
        for m in re.finditer(r'.*\\'+s+r'(\[[^[\]]*\])?{([^{}]+)}.*',
                             self.content()):
          io.dbg(*m.groups())
          file = BibFile(common.pathRelTo(self, m.groups()[-1]))
          if not file.exists():
            io.warn(f'file "{self.path}" included',
                    f'bibliography file "{file.path}"',
                    f'which does not seem to exist')
            (self.toplevel or self)._bibHealthy = False
          if file not in res:
            res.append(file)
      self._bibs = res
    return self._bibs


  def bibHealthy(self):
    if self._bibHealthy is None:
      if self.toplevel and self.toplevel._bibHealthy is not None:
        self._bibHealthy = self.toplevel._bibHealthy
      else:
        self.bibs()
        if (self.toplevel or self)._bibHealthy is None:
          self._bibHealthy = True
    return self._bibHealthy

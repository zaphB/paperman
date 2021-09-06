import re
import os

from .. import io
from .. import cfg
from .. import utils
from . import common

from .bib import BibFile
from .img import ImgFile
from .cite import Cite

class TexFile:
  def __init__(self, path, toplevel=None, raiseOnIncludeNotFound=None,
               enableIncludeImport=False):
    if not os.path.exists(path):
      raise RuntimeError(f'file {path} does not exist')

    self.path = os.path.normpath(path)
    self.toplevel = toplevel
    self.raiseOnIncludeNotFound = raiseOnIncludeNotFound
    self.enableIncludeImport = enableIncludeImport
    self._bibHealthy = None
    self._packageIncludes = None


  def __repr__(self):
    return f'tex file: {self.path}'


  def __eq__(self, file):
    return self.path and file.path and self.path == file.path


  def __lt__(self, file):
    return self.path and file.path and self.path < file.path


  def __gt__(self, file):
    return self.path and file.path and self.path > file.path


  @utils.cacheReturnValue
  def content(self):
    return '\n'.join([l.rstrip('\n') for l in open(self.path, 'r')
                        if not l.strip().startswith('%')])


  @utils.cacheReturnValue
  def enumContent(self):
    return [(i+1, l.rstrip('\n')) for i, l in enumerate(open(self.path, 'r'))
                                          if not l.strip().startswith('%')]


  def recurseThroughIncludes(self):
    for i in self.includes():
      i.recurseThroughIncludes()


  @utils.cacheReturnValue
  def includes(self):
    res = []
    if re.search(r'\\include(\[[^[\]]*\])?\{([^{}]+)\}', self.content()):
      io.warn(r'found \include{} command in tex file ',
              f'"{self.path}"',
              r'paperman does not support include logic and',
              r'might oversee missing/unused imgs/citation/includes')
    for m in re.finditer(r'\\input(\[[^[\]]*\])?\{([^{}]+)\}', self.content()):
      fname = m.groups()[-1]
      if not fname.endswith('.tex'):
        fname += '.tex'
      includePath = common.pathRelTo(self, fname)

      # if enabled, import missing include file
      if not os.path.isfile(includePath):
        if self.enableIncludeImport:
          from .. import finder
          if finder.importInclude(includePath):
            io.info(f'successfully imported {includePath}')

      # check again if file still missing and raise special exception
      # in case this is set (used by inputs subcommand)
      if not os.path.isfile(includePath):
        if self.raiseOnIncludeNotFound:
          raise self.raiseOnIncludeNotFound(includePath)

      # create TexFile and add to results
      res.append(TexFile(includePath,
                         toplevel=(self.toplevel or self),
                         raiseOnIncludeNotFound=self.raiseOnIncludeNotFound,
                         enableIncludeImport=self.enableIncludeImport))
    if res:
      io.verb(f'found include files of {self.path}: ',
              *[i.path for i in res])
    return res


  @utils.cacheReturnValue
  def isToplevel(self):
    return (all([re.search(s, self.content())
                      for s in (r'\\begin\{document\}',
                                r'\\end\{document\}')])
            and self.toplevel is None)


  @utils.cacheReturnValue
  def graphicspath(self, paths=[], latexlines=[]):
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
    for m in re.finditer(r'\\graphicspath\{((\s*\{[^{}]+\}\s*)+)\}',
                         self.content()):
      latexlines.append([self.path, m.string[m.start():m.end()]])
      _p = [m.groups()[0] for m in re.finditer(r'\{([^{}]*)\}',
                                                  re.sub(r'\s+', '', m.groups()[0]))]
      detectedPaths([common.pathRelTo(self, p) for p in _p])

    for p in paths:
      if not os.path.isdir(p):
        io.verb(f'found graphicspath {p}, which does not exist, ignoring')
    res = [p for p in paths if os.path.isdir(p)]
    if res:
      io.verb(f'found graphicspaths of {self.path}: '
              f'{", ".join(res)}')
    return res


  @utils.cacheReturnValue
  def imgs(self):
    res = []
    for i in self.includes():
      for file in i.imgs():
        if file not in res:
          res.append(file)
    for m in re.finditer(r'\\includegraphics(\[[^[\]]*\])?\{([^{}]+)\}', self.content()):
      file = ImgFile(m.groups()[-1], paths=self.graphicspath())
      if file not in res:
        res.append(file)
        if os.path.sep in file.fname:
          io.warn(f'in file "{self.path}":',
                  '"'+m.string[m.start():m.end()]+'"',
                  r'it is recommended to define image folders in the preample with',
                  r'\graphicspath{} and to use only names in \includegraphics '
                  f'calls, e.g.:',
                  f'\\graphicspath{{ ... {{{os.path.dirname(file.fname)+os.path.sep}}} ... }}'
                  f'and',
                  f'\\includegraphics[ ... ]{{{os.path.basename(file.fname)}}}')
    return res


  @utils.cacheReturnValue
  def bibs(self):
    res = []
    if self.toplevel is None:
      self._packageIncludes = 0
    elif self.toplevel._packageIncludes is None:
      raise ValueError('TexFile.bibs() method should only be called directly '
                       'on toplevel files')

    for i in self.includes():
      for b in i.bibs():
        if b not in res:
          res.append(b)

    # search for biblatex package loading
    for m in re.finditer(r'\\usepackage(\[[^[\]]*\])?{biblatex}',
                         self.content()):
      (self.toplevel or self)._packageIncludes += 1
      options = ''
      if len(m.groups()):
        options = m.groups()[0]
      m = re.search(r'backend\s*=\s*biber', options)
      if not m:
        io.warn(f'in file "{self.path}":',
                '"'+m.string[m.start():m.end()]+'"',
                f'it is recommended to use biblatex with backend=biber option')

    # search for deprectaed natbib and warn
    for m in re.finditer(r'\\usepackage(\[[^[\]]*\])?{natbib}',
                         self.content()):
      (self.toplevel or self)._packageIncludes += 1
      io.warn(f'in file "{self.path}":',
              '"'+m.string[m.start():m.end()]+'"',
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
        file = BibFile(common.pathRelTo(self, m.groups()[-1]))
        if not file.exists():
          io.warn(f'file "{self.path}" included',
                  f'bibliography file "{file.fname}"',
                  f'which does not seem to exist')
          (self.toplevel or self)._bibHealthy = False
        if file not in res:
          res.append(file)
    return res


  def bibHealthy(self):
    if self._bibHealthy is None:
      if self.toplevel and self.toplevel._bibHealthy is not None:
        self._bibHealthy = self.toplevel._bibHealthy
      else:
        self.bibs()
        if (self.toplevel or self)._bibHealthy is None:
          self._bibHealthy = True
    return self._bibHealthy


  @utils.cacheReturnValue
  def cites(self):
    res = []
    # scan through all commands that look like cite commands
    for m in re.finditer(r'\\[^\[\]{}]*cite[^\[\]{}]*(\[[^[\]]*\])?{([^{}]+)}',
                         self.content()):
      for s in m.groups()[-1].split():
        for _s in s.split(','):
          if _s.strip():
            cite = Cite(_s.strip(), self.bibs())
            if cite not in res:
              res.append(cite)
    return res


  @utils.cacheReturnValue
  def missingCites(self):
    return [c for c in self.cites() if c.isHealthy() and not c.exists()]


  @utils.cacheReturnValue
  def lint(self):
    for i in self.includes():
      yield i.lint()

    for ln, l in self.enumContent():
      # search for dollars without line break protection
      i = -1
      lastOpening = None
      opening = True
      while True:
        i = l.find('$', i+1)
        if i < 0:
          break
        if opening:
          lastOpening = i
          opening = False
        else:
          extr = l[lastOpening:i+1]
          opening = True
          if re.search(r'\$[^{].*\s.*[^}]\$', extr):
            yield (self.path, ln,
                   f'"{extr}"\n'
                   'math should be wrapped in curly braces to avoid\n'
                   'line breaks: not $a = b$ but ${a = b}$')

      # find commands that should not used or not be used in toplevel files
      avoidCommands = list(cfg.get('lint', 'avoid_commands'))
      if self.isToplevel():
        avoidCommands += list(cfg.get('lint', 'avoid_commands_in_toplevel'))
      for cmd in avoidCommands:
        cmd = cmd.strip(r'\ {}')
        if len(cmd) == 1:
          io.warn(f'command {cmd} in avoid_commands list is only one '
                   'character long')
        if re.search('\\\\'+cmd, l):
          bs = '\\'
          yield (self.path, ln,
                 f'found latex command {bs}{cmd}, which is on avoid-list')

      # spellcheck
      # TODO

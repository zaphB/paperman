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
    with open(self.path, 'r') as f:
      return '\n'.join([l.rstrip('\n') for l in f
                                if not l.strip().startswith('%')])


  @utils.cacheReturnValue
  def enumContent(self):
    with open(self.path, 'r') as f:
      return [(i+1, l.rstrip('\n')) for i, l in enumerate(f)
                                  if not l.strip().startswith('%')]


  def recurseThroughIncludes(self):
    for i in self.includes():
      i.recurseThroughIncludes()


  @utils.cacheReturnValue
  def includes(self):
    res = []
    if re.search(r'\\include\s*(\[[^[\]]*\])?\s*\{([^{}]+)\}', self.content()):
      io.warn(r'found \include{} command in tex file ',
              f'"{self.path}"',
              r'paperman does not support include logic and',
              r'might oversee missing/unused imgs/citation/includes')
    for m in re.finditer(r'\\input\s*(\[[^[\]]*\])?\s*\{([^{}]+)\}', self.content()):
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
      # in case this is set (used by input subcommand)
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
    for m in re.finditer(r'\\graphicspath\s*\{((\s*\{[^{}]+\}\s*)+)\}',
                         self.content()):
      latexlines.append([self.path, m.string[m.start():m.end()]])
      _p = [m.groups()[0] for m in re.finditer(r'\{([^{}]*)\}',
                                               re.sub(r'\s+', '', m.groups()[0]))]
      detectedPaths([common.pathRelTo(self, p) for p in _p])

    for p in paths:
      if not os.path.isdir(p):
        if (os.path.basename(p) == cfg.get('img_dir_name')
              or p == cfg.get('img_dir_name')):
          io.info(f'found graphicspath "{p}", which does not exist but matches '
                  f'the configured img_dir_name ("{cfg.get("img_dir_name")}"), '
                  'creating directory...')
          os.makedirs(p, exist_ok=True)
        else:
          io.info(f'found graphicspath {p}, which does not exist, ignoring')
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
    for m in re.finditer(r'\\includegraphics\s*(\[[^[\]]*\])?\s*\{([^{}]+)\}',
                         self.content()):
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
    for m in re.finditer(r'\\usepackage\s*(\[[^[\]]*\])?\s*{biblatex}',
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
    for m in re.finditer(r'\\usepackage\s*(\[[^[\]]*\])?\s*{natbib}',
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
      for m in re.finditer(r'.*\\'+s+r'\s*(\[[^[\]]*\])?\s*{([^{}]+)}.*',
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
    for m in re.finditer(r'\\[^\[\]{}]*cite\s*[^\[\]{}]*\s*(\[[^[\]]*\])?{([^{}]+)}',
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
  def lint(self, visited=[]):

    # lint included files
    for i in self.includes():
      if i not in visited:
        for l in i.lint(visited=visited):
          yield l
        visited.append(i)

    # lint included bib files
    for b in self.bibs():
      if b not in visited:
        for l in b.lint(visited=visited):
          yield l
        visited.append(b)

    # detect author entries and check whether they exist in whitelist
    authorPattern = r'([^\n]*)\\author\{([^}]*)\}([^\n]*)'
    knownAuthors = list(cfg.get('lint', 'known_authors'))

    for pre, authorName, post in re.findall(authorPattern, self.content(), re.M):
      # skip lines marked as ok:
      textAround = pre + ' ' + post
      if 'nolint' in textAround.split() or '%nolint' in textAround.split():
        continue
      
      # ask if author name should be added, complain otherwise
      authorName = authorName.strip()
      if authorName not in knownAuthors:
        if io.conf(f'found author {authorName} which is not in known_authors list, ',
                   f'add to list?', default=False):
          knownAuthors = knownAuthors+[authorName]
          cfg.set('lint', 'known_authors', knownAuthors)
        else:
          yield (self.path, '?',
                 f'author name {authorName} is not in known_authors list')


    for ln, l in self.enumContent():
      # skip lines marked as ok:
      if 'nolint' in l.split() or '%nolint' in l.split():
        continue

      # skip commented lines
      if l.strip().startswith('%'):
        continue

      # search for dollars without line break protection
      i = -1
      lastOpening = None
      opening = True
      doWarn = False
      while True:
        i = l.find('$', i+1)
        if i < 0:
          break
        if opening:
          lastOpening = i
          opening = False
          if l[i-1] != '}' and l[i+1] != '{':
            doWarn = True
        else:
          extr = l[lastOpening:i+1]
          opening = True
          doWarn = False
          #print(extr[1], extr[-2], re.search(r'[^a-zA-Z0-9\\S]', extr))
          if ((extr[1] != '{' or extr[-2] != '}')
                and re.search(r'[^a-zA-Z0-9\{\\S]', extr[2:-2])):
            yield (self.path, ln,
                   f'"{extr}"\n'
                   'math should be wrapped in curly braces to avoid\n'
                   'line breaks: not $a = b$ but ${a = b}$')
      if doWarn:
        yield (self.path, ln,
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

      # detect words in avoid list
      avoidWords = list(cfg.get('lint', 'avoid_words'))
      for word in avoidWords:
        # \b matches "word boundaries", i.e. white-spaces, string start/end etc.
        if re.search(r'\b'+word.lower()+r'\b', l.lower()):
          yield (self.path, ln,
                 f'found word {word}, which is on avoid-list')

      # find double words
      _l = re.sub(r'\s+', ' ', l.replace(',', '').replace('.', ''))
      for w1, w2 in zip(_l.split()[:-1], _l.split()[1:]):
        if w1 == w2 and re.match(r'[a-zA-Z0-9]', w1):
          yield (self.path, ln,
                 f'found duplicate word "{w1}"')

      # detect commas before that and because
      for word in ('because', 'that'):
        if re.search(r',\s*'+word, l.lower()):
          yield (self.path, ln,
                 f'found comma before {word}')

      # spellcheck
      # TODO

    visited.append(self)

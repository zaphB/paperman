import os
import re

from .. import cfg
from .. import io
from .. import utils
from . import common

from .cite import Cite, FORBIDDEN_KEY_CHARS


class BibFile:
  def __init__(self, fname):
    self.fname = os.path.normpath(fname)
    self.path = None
    if self.exists():
      self.path = self.exists()
      self._exists = True


  @utils.cacheReturnValue
  def exists(self):
    d = os.path.dirname(self.fname) or '.'
    if not os.path.isdir(d):
      return False
    for ext in ['']+list(cfg.get('bibtex_extensions')):
      candidate = utils.replaceSuffix(self.fname, ext)
      #io.dbg(f'trying candidate {candidate}')
      if os.path.isfile(candidate):
        return candidate
    return False


  @utils.cacheReturnValue
  def content(self):
    if self.path:
      with open(self.path, 'r') as f:
        return '\n'.join([l.rstrip('\n') for l in f])
    return ''


  @utils.cacheReturnValue
  def cites(self):
    res = []

    # parsing whole file with a characterwise state machine is the only
    # safe way to go...
    state = 'comment'
    currentSection = None
    currentKey = None
    currentItem = None
    currentValue = None
    currentValueParseInfo = None
    currentLine = 1
    previousBackslash = False
    braceDepth = None
    quoteDepth = None
    c = None

    def raiseErr(msg):
      nonlocal currentLine, state, c
      if cfg.get('debug'):
        allLines = self.content().split('\n')
        lines = allLines[max(0, currentLine-5):min(len(allLines), currentLine+5)]
        pretty = [('=> ' if i+1+max(0, currentLine-5) == currentLine else '>  ')+l
                    for i, l in enumerate(lines)]
      raise RuntimeError(f'in bib file {self.path} (line {currentLine}):\n'
                         +('\n'.join(pretty)+'\n'
                           +f'parser state "{state}", current char {repr(c)}\n'
                                                  if cfg.get('debug') else '')
                         +f'parsing error, {msg}')

    def _assert(expr, msg='unexpected error'):
      if not expr:
        raiseErr(msg)

    # function to call whenever an item-value pair is completed
    def flushItemValue():
      nonlocal currentItem, currentValue, currentValueParseInfo, braceDepth, quoteDepth
      currentItem = currentItem.strip()
      _assert(currentItem,
              'found empty item name')
      _assert(all([(c.isalpha() or c in '-_') for c in currentItem]),
              f'found invalid item name "{currentItem.strip()}"')
      _assert(len(res))
      if res[-1].fields is None:
        res[-1].fields = {}
      if res[-1].fieldsParseInfo is None:
        res[-1].fieldsParseInfo = {}
      if currentItem in res[-1].fields:
        raiseErr(f'duplicate item "{currentItem}"')

      # strip content between outermost braces/quotes
      if ('opens' in currentValueParseInfo
          and 'closes' in currentValueParseInfo
          and len(_opens := currentValueParseInfo['opens'])
          and len(_closes := currentValueParseInfo['closes'])):
        # extract content between outermost curly braces
        _o, _c = _opens[0], _closes[-1]
        midPart = currentValue[_o+1:_c]

        # shift last closing index according to removed spaces
        _closes[-1] -= len(midPart) - len(midPart.strip())

        # replace currentValue with stripped variant
        currentValue = (currentValue[:_o+1]
                        + midPart.strip()
                        + currentValue[_c:]
                       ).strip()

      res[-1].fields[currentItem] = currentValue.strip()
      res[-1].fieldsParseInfo[currentItem] = currentValueParseInfo
      #io.dbg(f'created new field for citation {res[-1].key}',
      #       f'item: {currentItem}, value: {currentValue}',
      #       f'parseInfo: {currentValueParseInfo}',
      #       f'in {self.path}:{currentLine}')
      currentValue = None
      currentValueParseInfo = None
      currentItem = None
      braceDepth = None
      quoteDepth = None

    for c in self.content():
      # @ sign while in "comment" -> transition to "section"
      if c == '@' and state == 'comment':
        _assert(currentSection is None)
        currentSection = ''
        state = 'section'
        #io.dbg(f'found start of new bib section',
        #       f'in {self.path}:{currentLine}')

      # skip all characters outside of sections
      elif state == 'comment':
        pass

      # { sign while in "section" -> transition to "key"
      elif c == '{' and state == 'section':
        _assert(currentSection is not None)
        _assert(currentSection.strip().isalpha(),
                f'invalid section name {repr(currentSection)}')
        _assert(currentKey is None)

        # special case section=comment: immediately transition
        # back to comment state
        if currentSection.strip().lower() == 'comment':
          currentSection = None
          state = 'comment'
        else:
          currentKey = ''
          state = 'key'

      # record any other character
      elif state == 'section':
        _assert(currentSection is not None)
        currentSection += c

      # , sign while in "key" -> transition to "item" and flush key and section
      elif c == ',' and state == 'key':
        _assert(currentSection is not None
                  and currentKey is not None)
        _assert(currentSection,
                'empty section name')
        _assert(currentKey,
                'empty key')
        res.append(Cite(currentKey,
                        bibs=[self],
                        section=currentSection))
        #io.dbg(f'created new citation entry with key {currentKey}',
        #       f'and type {currentSection}',
        #       f'in {self.path}:{currentLine}')
        currentKey = None
        currentSection = None

        _assert(currentItem is None)
        currentItem = ''
        state = 'item'

      # finding closing curly brace in key means bibtex entry without any items,
      # flush key and section and transition to comment state
      elif c == '}' and state == 'key':
        _assert(currentItem is None
                  and currentValue is None)
        res.append(Cite(currentKey,
                        bibs=[self],
                        section=currentSection))
        #io.dbg(f'created new empty citation entry with key {currentKey}',
        #       f'and type {currentSection}',
        #       f'in {self.path}:{currentLine}')
        currentKey = None
        currentSection = None
        state = 'comment'

      # any other character records key
      elif state == 'key':
        _assert(currentKey is not None)
        if len(currentKey.strip()):
          _assert(c not in ' \n\t',
                  f'unexpected end of citation key "{currentKey}", expected ","')
        _assert(c not in FORBIDDEN_KEY_CHARS,
                f'forbidden charcter in citation key: {repr(c)}')
        currentKey += c

      # = sign while in "item" -> transition to "value" and flush key and section
      elif c == '=' and state == 'item':
        state = 'value'
        _assert(currentSection is None
                  and currentKey is None)
        _assert(braceDepth is None
                  and quoteDepth is None
                  and currentValue is None)
        braceDepth = 0
        quoteDepth = 0
        currentValue = ''
        currentValueParseInfo = dict(opens=[], closes=[])

      # if a closing curly brace is encountered in item state and the current
      # item is empty, this means the section has ended, then flush everything
      # and transition to comment state
      elif c == '}' and state == 'item':
        _assert(currentItem.strip() == '')
        currentItem = None
        _assert(currentSection is None
                  and currentKey is None
                  and currentValue is None)
        state = 'comment'

      # record all other characters as item name
      elif state == 'item':
        _assert(currentItem is not None)
        _assert(currentItem.strip() == ''
                  or all([(c.isalpha()
                              or c.strip() == ''
                              or c in '-_') for c in currentItem]),
                f'found invalid item name starting with "{currentItem.strip()}"')
        currentItem += c

      # nice summary of how {, } and " delimiters are parsed by bibtex:
      # https://tex.stackexchange.com/questions/109064/is-there-a-difference-between-and-in-bibtex
      #
      # value parsing in short:
      # * do not consume curly braces, always error on unmatched curly braces.
      # * do not consume double-quotes only count depth and error on unmatched
      #   double-quotes only if not within {}
      # * treat single quotes as normal character
      # * backslash escapes {, }, but still count depth to guarantee matching
      # * backslash escapes double-quotes
      # * if any different character follows backslash, treat backslash as
      #   normal character
      elif state == 'value':

        # if previous character was a backslash, modify current character
        # such that it will be treated as normal character
        if previousBackslash:
          c = '\\'+c
          previousBackslash = False

        # do not handle backslash now but only set previousBackslash flag
        if c == '\\':
          previousBackslash = True

        # { sign while in "value" -> increment braceDepth
        elif c == '{':
          _assert(braceDepth is not None)
          braceDepth += 1
          _assert(currentValue is not None)
          currentValue = currentValue.lstrip()
          currentValueParseInfo['opens'].append(len(currentValue))
          currentValue += c

        # a seemingly unmatched } in value state means that citation is
        # complete, flush everything and transition to "comment" state
        elif c == '}' and braceDepth == 0 and quoteDepth == 0:
          flushItemValue()
          _assert(currentSection is None
                    and currentKey is None
                    and currentItem is None
                    and currentValue is None)
          state = 'comment'

        # } sign while in "value" -> decrement braceDepth
        elif c == '}':
          _assert(braceDepth is not None and braceDepth > 0,
                  'found unmatched "}"')
          braceDepth -= 1
          _assert(currentValue is not None)
          currentValue = currentValue.lstrip()
          currentValueParseInfo['closes'].append(len(currentValue))
          currentValue += c

        # " sign while in "value" -> toggle quote depth if not within
        # curly braces, add to currentValue anyways
        elif c == '"' and state == 'value' and braceDepth == 0:
          _assert(quoteDepth is not None)
          currentValue = currentValue.lstrip()
          if quoteDepth:
            currentValueParseInfo['closes'].append(len(currentValue))
          else:
            currentValueParseInfo['opens'].append(len(currentValue))
          quoteDepth = (1 if quoteDepth == 0 else 0)
          currentValue += c

        # add escaped curly brace to content and also increment depth
        elif c == r'\{':
          _assert(braceDepth is not None)
          braceDepth += 1
          currentValue += c

        # add escaped curly brace to content and also decrement depth
        elif c == r'\}':
          _assert(braceDepth is not None and braceDepth > 0,
                  'found unmatched "}"')
          braceDepth -= 1
          currentValue += c

        # , sign with balanced braces and quotes flushes current item value
        # pair and leaves value mode
        elif c == ',' and braceDepth == 0 and quoteDepth == 0:
          flushItemValue()
          currentItem = ''
          state = 'item'

        # any other character is just added to content
        else:
          currentValue += c

      else:
        _assert(state == 'comment',
                f'unexpected character {repr(c)}')

      # increase line counter on newlines no matter what state
      if c == '\n':
        currentLine += 1

    _assert(currentSection is None
                and currentKey is None
                and currentItem is None
                and currentValue is None
                and previousBackslash is False
                and braceDepth is None
                and quoteDepth is None
                and state == 'comment',
            'citation section was started but never ended,\n'
            'probably due to unmatched curly braces')

    return res


  def _duplicates(self):
    byKey, byGeneratedKey, byCompareAuthorTitle = {}, {}, {}
    for cite in self.cites():
      for d, k in zip([byKey, byGeneratedKey, byCompareAuthorTitle],
                      [cite.key, cite.makeKey(), cite.compareAuthorTitle()]):
        if k not in d.keys():
          d[k] = []
        d[k].append(cite)
    return [ [c for c in d.values() if len(c)>1]
                    for d in (byKey, byGeneratedKey, byCompareAuthorTitle) ]

  
  def duplicatesKeys(self):
    return self._duplicates()[0]


  def duplicatesGeneratedKeys(self):
    return self._duplicates()[1]


  def duplicatesAuthorTitle(self):
    return self._duplicates()[2]


  def addCites(self, cites):
    if cites:
      with open(self.path, 'a') as f:
        f.write('\n'+'\n\n'.join([c.pretty() for c in cites])+'\n')
      self._cites = None
      self.cites()


  def setCites(self, cites):
    newContent = '\n\n'.join([c.pretty() for c in cites])+'\n'
    if newContent != self.content:
      with open(self.path, 'w') as f:
        f.write(newContent)
      self._cites = None
      self.cites()


  def rewrite(self):
    self.setCites(self.cites())


  def create(self):
    if not self.exists():
      fname = self.fname
      with open(utils.replaceSuffix(fname, cfg.get('bibtex_extensions')[0]), 'a') as f:
        pass
      self.__dict__ = {}
      self.__init__(fname)


  def fromRis(key, risFile):
    entries = dict()
    entries['authors']=list()

    with open(risFile) as f:
      prevKey = None
      for line in f:
        if not line.strip():
          continue

        # lines beginning with two capital letters correspond to bibtex fields
        if re.match("PY",line):
          prevKey = 'year'
          entries['year'] = line[6:10]
        elif re.match("AU",line):
          prevKey = 'authors'
          entries['authors'].append(line[6:-1])
        elif re.match("VL",line):
          prevKey = 'volume'
          entries['volume'] = line[6:-1]
        elif re.match("TI",line):
          prevKey = 'title'
          entries['title'] = line[6:-1]
        elif re.match("T1",line):
          prevKey = 'title'
          entries['title'] = line[6:-1]
        elif re.match("JO",line):
          prevKey = 'journal'
          entries['journal'] = line[6:-1]
        elif re.match("IS",line):
          prevKey = 'number'
          entries['number'] = line[6:-1]
        elif re.match("SP",line):
          prevKey = 'startpage'
          entries['startpage'] = line[6:-1]
        elif re.match("EP",line):
          prevKey = 'endpage'
          entries['endpage'] = line[6:-1]
        elif re.match("SN",line):
          prevKey = 'isbn'
          entries['isbn'] = line[6:-1]
        elif re.match("AB",line):
          prevKey = 'abstract'
          entries['abstract'] = line[6:-1]
        elif re.match("UR",line):
          prevKey = 'url'
          entries['url'] = line[6:-1]

        # join lines not beginning with two capital letters and a hyphen to previous line
        elif not re.match(r'[A-Z0-9][A-Z0-9]\s*-', line):
          if prevKey not in entries.keys():
            raise ValueError(f'unexpected line in ris file: {line}')
          if prevKey == 'authors':
            entries[prevKey][-1] += ' '+line
          else:
            entries[prevKey] += ' '+line


    bibStr = ('@article{' + key + ',\n'
                  + 'author={' + (" and ".join(entries['authors'])) + '},\n'
                  + 'year={' + entries['year'] + '},\n'
                  + 'title={' + entries['title'] + '},\n'
                  + ('abstract' in entries) * ('abstract = {' + entries.get('abstract', '') + '},\n')
                  + ('journal' in entries) * ('journal={' + entries.get('journal', '') + '},\n')
                  + ('volume' in entries) * ('volume={' + entries.get('volume', '') + '},\n')
                  + ('startpage' in entries and 'endpage' in entries)
                      * ('pages={' + entries.get('startpage', '')
                          + "--" + entries.get('endpage', '') + '},\n')
                  + 'url={'+entries['url']+'},\n'
                  + '}\n')
    io.dbg('converted ris to bib: ', bibStr)
    res = BibFile('')
    res._content = bibStr
    return res


  def lint(self, visited=[]):
    reported = []

    # report duplicates
    for duplicates in self.duplicatesKeys():
      if duplicates not in reported:
        reported.append(duplicates)
        yield (self.path, '?', f'found bib entries with duplicate '
                  f'key {duplicates[0].key}')

    for duplicates in self.duplicatesGeneratedKeys():
      if duplicates not in reported:
        reported.append(duplicates)
        yield (self.path, '?', f'found bib entries with conflicting generated '
                  f'keys:\n{", ".join([d.key for d in duplicates])}')

    for duplicates in self.duplicatesAuthorTitle():
      if duplicates not in reported:
        reported.append(duplicates)
        yield (self.path, '?', f'found bib entries with identical authors and title:\n'
                  f'{", ".join([d.key for d in duplicates])}')

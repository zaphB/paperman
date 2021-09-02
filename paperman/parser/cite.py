import re

from .. import io
from .. import cfg
from .. import utils

FORBIDDEN_KEY_CHARS = r'''#'",=(){}%~\ '''


def shouldBeProtected(fullString, string, askProtect=True):
  protectedList = [s.strip()
                        for s in cfg.get('z_bib_words_protect_capitalization')]
  antiProtectedList = [s.strip()
                        for s in cfg.get('z_bib_words_dont_protect_capitalization')]
  string = string.strip()
  if string in antiProtectedList:
    return False
  if string in protectedList:
    return True
  decision = True
  if askProtect:
    decision = io.conf(f'should the capitalization of ',
                       f'"{string}" in',
                       f'"{fullString}"',
                       f'be protected  in the bibliography?', default=True)
  if decision:
    if io.conf(f'should protected capitalization of',
               f'"{string}"',
               f'be saved permanently?', default=True):
      protectedList.append(string.lower())
      cfg.set('z_bib_words_protect_capitalization',
              sorted(list(set(protectedList))))
  else:
    if io.conf(f'should never capitalizing',
               f'"{string}"',
               f'be saved permanently?', default=True):
      antiProtectedList.append(string.lower())
      cfg.set('z_bib_words_dont_protect_capitalization',
              sorted(list(set(antiProtectedList))))
  return decision


class Cite:
  def __init__(self, key, bibs=None, section=None, fields=None):
    self.key = key.strip()
    self.bibs = bibs
    self.section = (None if section is None else section.strip().lower())
    self.fields = fields
    self.fieldsParseInfo = None


  def __repr__(self):
    return f'citation {self.key}'+('' if self.isHealthy() else ' (unhealthy)')


  def __eq__(self, cite):
    return self.key == cite.key


  def __gt__(self, cite):
    return self.key > cite.key


  def __lt__(self, cite):
    return self.key < cite.key


  def __getitem__(self, item):
    _, val = self._findFieldKeyValuePair(item)
    return val


  def __setitem__(self, item, value):
    k, val = self._findFieldKeyValuePair(item)

    # pop item element
    self.fields.pop(k)

    # pop parse info as well, which is useless after setting a new value
    if (self.fieldsParseInfo is not None
            and k in self.fieldsParseInfo):
      self.fieldsParseInfo.pop(k)

    # set new value
    self.fields[item.lower()] = '{'+str(value)+'}'


  # return item from self.items with case insensitive matching
  def _findFieldKeyValuePair(self, item):
    if self.fields is None:
      return None, None

    keys = list(self.fields.keys())
    lkeys = [k.lower() for k in keys]
    if item.lower() not in lkeys:
      return None, None

    k = keys[lkeys.index(item.lower())]

    # only return if field has expected form
    if (self.fields[k]
          and self.fields[k][0] in '{"'
          and self.fields[k][-1] in '}"'):
      return k, self.fields[k][1:-1]
    return None, None


  @utils.cacheReturnValue
  def isHealthy(self):
    # list of forbidden characters in bibtex keys found here:
    # https://tex.stackexchange.com/questions/408530/what-characters-are-allowed-to-use-as-delimiters-for-bibtex-keys
    return all([c not in self.key for c in FORBIDDEN_KEY_CHARS])


  @utils.cacheReturnValue
  def exists(self):
    if self.bibs is None:
      return None
    for b in self.bibs:
      if self in b.cites():
        return True
    return False


  @utils.cacheReturnValue
  def pretty(self):
    fieldsStr = ''
    if self.fields is not None:
      # replace url field if doi field exists
      if (cfg.get('bib_repair', 'generate_url_from_doi')
                and (doi := self['doi']) is not None):
        self['doi'] = doi
        self['url'] = f'https://doi.org/{doi}'

      # reformat pages field if exists
      if (cfg.get('bib_repair', 'force_double_hyphen_in_pages')
                and (pages := self['pages']) is not None):
        if m := re.match(r'(\d+)[-\s]+(\d+)', pages):
          self['pages'] = m.groups()[0]+'--'+m.groups()[1]

      # replace url field if doi field exists
      if (cfg.get('bib_repair', 'convert_month_to_number')
                and (month := self['month']) is not None):
        try:
          self['month'] = int(month)
        except:
          raise
          months = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()
          for i, m in enumerate(months):
            if month.lower().startswith(m):
              self['month'] = i+1
              break
          else:
            io.warn(f'found invalid month "{month}" in citation "{self.key}", '
                    f'ignoring...')

      # check if config for journal conversion is consistent
      if (cfg.get('bib_repair', 'convert_journal_to_iso4_abbr')
            and cfg.get('bib_repair', 'convert_journal_to_fullname')):
        raise RuntimeError('invalid "bib_repair" config: both',
                           '"convert_journal_to_iso4_abbr" and',
                           '"convert_journal_to_fullname" are enabled')

      # replace url field if doi field exists
      if (cfg.get('bib_repair', 'convert_journal_to_iso4_abbr')
                and (journal := self['journal']) is not None):
        raise RuntimeError('not implemented')

      # replace url field if doi field exists
      if (cfg.get('bib_repair', 'convert_journal_to_fullname')
                and (journal := self['journal']) is not None):
        raise RuntimeError('not implemented')


      for k, v in self.fields.items():
        # skip ignore fields
        if k in cfg.get('bib_repair', 'remove_fields'):
          continue

        # try to reformat curly braces etc. if parse info is available
        if (self.fieldsParseInfo is not None
              and k in self.fieldsParseInfo):
          opens, closes = [self.fieldsParseInfo[k][_k]
                                      for _k in ('opens', 'closes')]
          if (not opens or not closes
                or len(opens) != len(closes)
                or opens[0] != 0
                or closes[-1] != len(v)-1):
            io.warn('unexpected curly brace and quote structure at',
                    f'citation with key "{self.key}" in item "{k}",',
                    'failed to pretty print this citation')
          else:
            # replace outer enclosure with curly braces
            opens.pop(0)
            closes.pop(-1)
            v = '{'+v[1:-1]+'}'

            # go through other opens and closes and check why they are there
            while len(opens):
              o = opens.pop(0)
              if closes[0] <= o:
                raise RuntimeError('unexpected error')
              if opens and closes[0] >= opens[0]:
                io.warn('unexpected curly brace and quote structure at',
                        f'citation with key "{self.key}" in item "{k}",',
                        'failed to pretty print this citation')
                break
              c = closes.pop(0)

              # detect if only single letters or fraction of a word are proteced
              _o, _c = o, c
              while _o > 0 and v[_o-1].isalpha() or v[_o-1] in '-':
                _o -= 1
              while _c+1 < len(v) and v[_c+1].isalpha() or v[_c+1] in '-':
                _c += 1
              _c = min(_c+1, len(v)-1)
              orig = v[o+1:c].replace('{', '').replace('}', '').replace('"', '')
              expanded = v[_o+1:_c].replace('{', '').replace('}', '').replace('"', '')
              askProtect = True
              if orig != expanded:
                if io.conf(f'detected protected capitalization fractional word',
                           f'"{v[o+1:c]}" in value',
                           f'"{v}"',
                           f'expand protection to '
                           f'"{expanded}"?', default=True):
                  # update value and open/close positions
                  v = v[:_o]+'{'+v[_o:o]+v[o+1:c]+v[c+1:_c]+'}'+v[_c:]
                  o = _o
                  c = _c-1

                  # remove other openings and closings in word range
                  while opens and opens[0] <= c:
                    opens.pop(0)
                    closes.pop(0)
                  askProtect = False

              # apply/dont apply protection
              if shouldBeProtected(v, v[o+1:c], askProtect=askProtect):
                v = v[:o]+'{'+v[o+1:c]+'}'+v[c+1:]
              else:
                v = v[:o]+v[o+1:c]+v[c+1:]
                opens = [o-2 for o in opens]
                closes = [c-2 for c in closes]

        # check if always protect phrases exist and offer protection
        if cfg.get('bib_repair', 'protect_capitalization_if_unprotected'):
          for protect in cfg.get('z_bib_words_protect_capitalization'):
            protect = protect.strip()
            i = -1
            while (i := v.find(protect, i+1)) >= 0:
              if ((i-1 < 0
                      or v[i-1] in ' ')
                  and (i+len(protect) > len(v)-2
                      or v[i+len(protect)] in ' ')):
                v = v[:i]+'{'+v[i:i+len(protect)]+'}'+v[i+len(protect):]

        if cfg.get('bib_repair', 'make_all_items_lowercase'):
          k = k.lower()
        fieldsStr += f'  {k} = {v},\n'

      # strip trailing comma+newline and wrap properly
      if fieldsStr:
        fieldsStr = f',\n{fieldsStr[:-2]}\n'

    return (f'@{self.section}{{{self.key}'+fieldsStr+'}')

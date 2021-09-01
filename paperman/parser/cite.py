from .. import io
from .. import cfg
from .. import utils

FORBIDDEN_KEY_CHARS = r'''#'",=(){}%~\ '''


def shouldBeProtected(string):
  protectedList = [s.strip().lower()
                        for s in cfg.get('z_bib_words_protect_capitalization')]
  antiProtectedList = [s.strip().lower()
                        for s in cfg.get('z_bib_words_dont_protect_capitalization')]
  string = string.strip()
  if string.lower() in antiProtectedList:
    return False
  if string.lower() in protectedList:
    return True
  decision = io.conf(f'should the capitalization of ',
                     f'"{string}"',
                     f'be protected  in the bibliography?', default=True)
  if io.conf(f'should this decision be saved permanently?', default=True):
    if decision:
      protectedList.append(string.lower())
      cfg.set('z_bib_words_protect_capitalization',
              sorted(protectedList))
    else:
      antiProtectedList.append(string.lower())
      cfg.set('z_bib_words_dont_protect_capitalization',
              sorted(antiProtectedList))
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

      # find key case-insensitively and remove it from
      # self.fields and self.fieldsParseInfo
      def popKey(k):
        keys = list(self.fields.keys())
        _keys = [_k.lower() for _k in keys]
        if k in _keys:
          _k = keys[_keys.index(k)]

          # only proceed if field has expected form
          if (self.fields[_k]
                and self.fields[_k][0] in '{"'
                and self.fields[_k][-1] in '}"'):

            # pop parse info as well
            if (self.fieldsParseInfo is not None
                    and _k in self.fieldsParseInfo):
              self.fieldsParseInfo.pop(_k)

            # return field value without enclosing chars
            return self.fields.pop(_k)[1:-1]
        return None

      # replace url field if doi field exists
      if (doi := popKey('doi')) is not None:
        popKey('url')
        self.fields['doi'] = f'{{{doi}}}'
        self.fields['url'] = f'{{https://doi.org/{doi}}}'


      for k, v in self.fields.items():
        # skip ignore fields
        if k in cfg.get('bib_ignore_fields'):
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
              if shouldBeProtected(v[o+1:c]):
                v = v[:o]+'{'+v[o+1:c]+'}'+v[c+1:]
              else:
                v = v[:o]+v[o+1:c]+v[c+1:]

        fieldsStr += f'  {k.lower()} = {v},\n'

      # strip trailing comma+newline and wrap properly
      if fieldsStr:
        fieldsStr = f',\n{fieldsStr[:-2]}\n'

    return (f'@{self.section}{{{self.key}'+fieldsStr+'}')

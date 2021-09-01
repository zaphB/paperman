from .. import io
from .. import utils


FORBIDDEN_KEY_CHARS = r'''#'",=(){}%~\ '''


class Cite:
  def __init__(self, key, bibs=None, section=None, fields=None):
    self.key = key.strip()
    self.bibs = bibs
    self.section = (None if section is None else section.strip().lower())
    self.fields = fields


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
    return (f'@{self.section}{{{self.key}'
            +(',\n'.join(['']+[f'  {k} = {v}'
                        for k, v in self.fields.items()
                                if k not in ('abstract', )])+'\n'
                  if self.fields else '')
            +'}')

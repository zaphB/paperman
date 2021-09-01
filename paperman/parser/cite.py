from .. import io
from .. import utils


FORBIDDEN_KEY_CHARS = r'''#'",=(){}%~\ '''


class Citation:
  def __init__(self, key, bibs=None, section=None, fields=None):
    self.key = key.strip()
    self.bibs = bibs
    self.section = section
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

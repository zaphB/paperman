import re
import requests
import cloudscraper
import time
import unidecode

from .. import io
from .. import cfg
from .. import utils

FORBIDDEN_KEY_CHARS = r'''#'",=(){}%~\ '''

@utils.cacheReturnValue
def hasNetwork():
  for _ in range(5):
    if _hasNetwork():
      return True
    time.sleep(1)
  return _hasNetwork()

def _hasNetwork():
  t0 = time.time()
  try:
    requests.get('https://pypi.org/project/paperman/', timeout=1)
    result = True
  except KeyboardInterrupt:
    raise
  except:
    io.warn('not connected to the internet, cannot check citation urls '
            'and dois')
    result = False

  # begin of workaround
  #  if ipv6 is misconfigured or not availabe requests.get(...) works
  #  but is extremely slow, because it only falls back to ipv4 after
  #  the timeout. This workaround (dirtily) detects misconfigured ipv6
  #  by measuring the time that requests.get(...) took and disables
  #  future use of ipv6 connections if it took longer than the
  #  timeout.
  if result and time.time()-t0 > 1:
    io.verb('disabling ipv6 connections')
    requests.packages.urllib3.util.connection.HAS_IPV6 = False
  # end of workaround

  return result


def isDoiValid(doi):
  io.dbg(f'verifying doi {doi}...')
  err = _isDoiOrUrlValid(doi, 'z_verified_dois',
                          prefix='https://doi.org/')
  if not err:
    return ''
  return f'invalid doi: {err}'


def isUrlValid(url):
  io.dbg(f'verifying url {url}...')
  err = _isDoiOrUrlValid(url, 'z_verified_urls')
  if not err:
    return ''
  return f'invalid url: {err}'


_cloudscraper = None

def _getScraper():
  global _cloudscraper
  if _cloudscraper is None:
    _cloudscraper = cloudscraper.create_scraper()
  return _cloudscraper


def _isDoiOrUrlValid(url, validCfgListKey, prefix=''):
  url = url.strip()
  try:
    verified = [(t, u) for t, u in cfg.get(validCfgListKey)
                      if time.time()-t < 30*24*60*60*cfg.get('bib_repair',
                              'doi_and_url_verification_max_age_months')]
  except KeyboardInterrupt:
    raise
  except:
    verified = []

  # check if in list
  if url in [u for t, u in verified]:
    result = ''

  # try to fetch urls
  else:
    result = ''
    #io.dbg(f'requesting {prefix+url}')
    r = None
    if hasNetwork():
      io.dbg(f'requesting url {prefix+url}')
      try:
        r = requests.get(prefix+url, timeout=5)
        if r.status_code//10 != 20:
          if 'cloudflare' in r.text.lower():
            raise ValueError('cloudflare protection')
          raise ValueError(f'status code is {r.status_code}')
      except KeyboardInterrupt:
        raise
      except Exception as _e:
        try:
          r = _getScraper().get(prefix+url, timeout=5)
          if r.status_code//10 != 20:
            raise ValueError(f'status code is {r.status_code}')
        except KeyboardInterrupt:
          raise
        except Exception as e:
          result = 'requests: '+str(_e)+', cloudscraper: '+str(e)

  if not result:
    verified.append((time.time(), url))

  cfg.set(validCfgListKey, verified)
  return result


_printedCloudflareWarning = False

def _printCloudflareWarning():
  global _printedCloudflareWarning
  if not _printedCloudflareWarning:
    io.warn(f'cloudflare protection prevented checking some URLs and/or DOIs')
    _printedCloudflareWarning = True


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
    decision = io.conf(f'in bib line',
                       f'"{fullString}"',
                       f'should the capitalization of ',
                       f'"{string}"',
                       f'be protected in the bibliography?', default=True)
  if decision:
    if io.conf(f'should protected capitalization of',
               f'"{string}"',
               f'be saved permanently?', default=True):
      protectedList.append(string)
      cfg.set('z_bib_words_protect_capitalization',
              sorted(list(set(protectedList))))
  else:
    if io.conf(f'should never capitalizing',
               f'"{string}"',
               f'be saved permanently?', default=False):
      antiProtectedList.append(string)
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


  def compareAuthorTitle(self):
    cmp = lambda a: re.sub(r'[^a-z0-9]+', '', a.lower()).replace('and', '')
    return 'cmp'+cmp(self.get('author', ''))+cmp(self.get('title', ''))


  def authorAndTitleEqual(self, cite):
    return self.compareAuthorTitle() == cite.compareAuthorTitle()


  def __gt__(self, cite):
    return self.key > cite.key


  def __lt__(self, cite):
    return self.key < cite.key


  def __getitem__(self, item):
    _, val = self._findFieldKeyValuePair(item)
    return val


  def get(self, item, default=None):
    res = self[item]
    if res is None:
      return default
    return res


  def __setitem__(self, item, value):
    k, val = self._findFieldKeyValuePair(item)
    if k is not None:
      # pop item element
      self.fields.pop(k)

      # pop parse info as well, which is useless after setting a new value
      if (self.fieldsParseInfo is not None
              and k in self.fieldsParseInfo):
        self.fieldsParseInfo.pop(k)

    # set new value
    value = str(value)
    if value[0] != '{' and value[-1] != '}':
      value = '{'+str(value)+'}'
    io.dbg(f'setting new field self.fields[{item.lower()}] = {repr(value)}',
           f'self.fieldsParseInfo[{item.lower()}] = {dict(opens=[0], closes=[len(value)-1])}')
    self.fields[item.lower()] = value
    self.fieldsParseInfo[item.lower()] = {'opens': [0],
                                          'closes': [len(value)-1]}


  # return item from self.items with case insensitive matching
  def _findFieldKeyValuePair(self, item):
    if self.fields is None:
      return None, None

    keys = list(self.fields.keys())
    lkeys = [k.lower() for k in keys]
    if item.lower() not in lkeys:
      return None, None

    k = keys[lkeys.index(item.lower())]

    # if limited by { and } or ", strip those
    f = self.fields[k]
    while (( f.strip().startswith('{') 
              and f.strip().endswith('}') )
        or ( f.strip().startswith('"') 
              and f.strip().endswith('"') ) ):
      f = f.strip()[1:-1]

    # return key and result
    return k, f


  def insertNonexistingItems(self, cite):
    lkeys = [k.lower() for k in self.fields.keys()]
    for k, v in cite.fields.items():
      if k not in lkeys:
        parseInfo = {}
        if k in v.fieldsParseInfo:
          parseInfo = v.fieldsParseInfo[k]
        _k = k
        if cfg.get('bib_repair', 'make_all_items_lowercase'):
          _k = k.lower()
        io.dbg(f'inserted field {_v}={v[:10]}{"" if len(v)<10 else "..."} into citation')
        self.fields[_k] = v
        self.fieldsParseInfo[_k] = parseInfo


  @utils.cacheReturnValue
  def isHealthy(self):
    # list of forbidden characters in bibtex keys found here:
    # https://tex.stackexchange.com/questions/408530/what-characters-are-allowed-to-use-as-delimiters-for-bibtex-keys
    return all([c not in self.key for c in FORBIDDEN_KEY_CHARS])


  @utils.cacheReturnValue
  def exists(self):
    #io.dbg(f'self.exists: {self.key=}, {[b.path for b in self.bibs]=}')
    if self.bibs is None:
      return None
    for b in self.bibs:
      if self in b.cites():
        #io.dbg(f'exsists in {b.path}')
        return True
    return False


  def toString(self):
    fieldsStr = ''
    for k, v in self.fields.items():
      fieldsStr += f'  {k} = {v},\n'
    # strip trailing comma+newline and wrap properly
    if fieldsStr:
      fieldsStr = f',\n{fieldsStr[:-2]}\n'
    return f'@{self.section}{{{self.key}'+fieldsStr+'}'


  def makeKey(self):
    res = []
    author, title, year = [self.get(k, '') for k in 'author title year'.split()]

    # add first author's lastname
    author = re.sub(r'[^a-z0-9,\s]+', '', unidecode.unidecode(author).lower())
    author = re.sub(r'\s+', ' ', author)
    if author:
      firstAuthor = author.split('and')[0]
      lastName = firstAuthor.split(',')[0].split()[-1]
      res.append(lastName.lower())

    # add title
    title = re.sub(r'[^a-z0-9\s]+', '', unidecode.unidecode(title).lower())
    if title:
      segments = [s.strip() for s in title.split() 
                    if s.strip() and s not in (
                        'in', 'of', 'for', 'by', 'the', 'and', 'a', 'on')]
      res.extend(segments[:2])

    # add year
    year = re.sub(r'[^a-z0-9\s]+', '', unidecode.unidecode(year).lower())
    if year:
      res.append(year)

    return '_'.join(res)


  def pretty(self):
    fieldsStr = ''
    if self.fields is not None:
      # strip http etc. from doi field if existing
      doi = self['doi']
      if (cfg.get('bib_repair', 'repair_doi')
          and doi is not None):
        for strip in ('http://doi.org/', 'https://doi.org/'):
          if doi.startswith(strip):
            self['doi'] = doi[len(strip):]
            break

      # replace url field if doi field exists
      doi = self['doi']
      url = self['url']
      if (cfg.get('bib_repair', 'generate_url_from_doi')
                and doi is not None
                and url is None):
        self['doi'] = doi
        self['url'] = f'https://doi.org/{doi}'

      # check if url is available if connected to the internet and url present
      url = self['url']
      if (cfg.get('bib_repair', 'verify_url_exists')
          and url is not None):
        err = isUrlValid(url)
        if err:
          if 'cloudflare' in err.lower():
            _printCloudflareWarning()
            io.dbg(f'citation {self.key} has {err}')
          else:
            io.warn(f'citation {self.key} has {err}')

      # check if doi is valid if connected to the internet and doi present
      doi = self['doi']
      if (cfg.get('bib_repair', 'verify_doi_exists')
          and doi is not None):
        err = isDoiValid(doi)
        if err:
          if 'cloudflare' in err.lower():
            _printCloudflareWarning()
            io.dbg(f'citation {self.key} has {err}')
          else:
            io.warn(f'citation {self.key} has {err}')

      # reformat pages field if exists
      pages = self['pages']
      if (cfg.get('bib_repair', 'keep_only_startpage_in_pages')
                and pages is not None):
        m = re.match(r'^(\d+)', pages)
        if m:
          self['pages'] = m.groups()[0]
      elif (cfg.get('bib_repair', 'force_double_hyphen_in_pages')
                and pages is not None):
        m = re.match(r'(\d+)[-\s]+(\d+)', pages)
        if m:
          self['pages'] = m.groups()[0]+'--'+m.groups()[1]

      # convert month field to number if given in string representation
      month = self['month']
      if (cfg.get('bib_repair', 'convert_month_to_number')
                and month is not None):
        try:
          self['month'] = int(month)
        except:
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
            and cfg.get('bib_repair', 'convert_journal_to_full_name')):
        raise RuntimeError('invalid "bib_repair" config: both',
                           '"convert_journal_to_iso4_abbr" and',
                           '"convert_journal_to_full_name" are enabled')

      # search for journal in library and ask to add it if not existing
      # replace journal field with library value
      jour = self['journal']
      if ((cfg.get('bib_repair', 'convert_journal_to_iso4_abbr')
             or cfg.get('bib_repair', 'convert_journal_to_full_name'))
                and jour is not None):
        from ..parser import journal
        abbr, name = journal.getOrAsk(jour, self.toString())
        if cfg.get('bib_repair', 'convert_journal_to_iso4_abbr'):
          res = abbr
        else:
          res = name
        if res != jour:
          io.verb('replaced journal field',
                  repr(jour),
                  'with',
                  repr(res))
        self['journal'] = res

      for k, v in self.fields.items():
        # skip ignore fields
        if k in cfg.get('bib_repair', 'remove_fields'):
          continue

        # try to reformat curly braces etc. if parse info is available
        if (self.fieldsParseInfo is not None
              and k in self.fieldsParseInfo):
          opens, closes = [self.fieldsParseInfo[k][_k]
                                      for _k in ('opens', 'closes')]
          if not opens and not closes:
            if v[0] != '{' and v[-1] != '}':
              v = '{'+v+'}'

          elif (len(opens) != len(closes)
                or opens[0] != 0
                or closes[-1] != len(v)-1):
            io.dbg(f'v={v}', f'opens={opens}', f'closes={closes}')
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
                #io.warn('curly brace/quote structure is nested too deeply in',
                #        f'citation with key "{self.key}" in item "{k}",',
                #        'failed to pretty print this citation')
                break
              c = closes.pop(0)

              # detect if only single letters or fraction of a word are proteced
              _o, _c = o, c
              while _o > 0 and (v[_o].isalpha() or v[_o] in r'\-{}'):
                _o -= 1
              while _c < len(v) and (v[_c].isalpha() or v[_c] in r'\-{}'):
                _c += 1
              orig = v[o+1:c].replace('{', '').replace('}', '')
              expanded = v[_o+1:_c].replace('{', '').replace('}', '')
              askProtect = True
              if ('\\' not in v[:_c+1]
                      and orig.strip()
                      and orig != expanded
                      and all([c not in expanded for c in r'/:_'])):
                if io.conf(f'detected protected capitalization of a fraction '
                           f'of a word in',
                           f'"{v}"',
                           f'expand "{v[o+1:c]}" -> "{expanded}"?', default=True):
                  # update value and open/close positions
                  v = v[:_o+1]+'{'+v[_o+1:o]+v[o+1:c]+v[c+1:_c]+'}'+v[_c:]
                  o = _o+1
                  c = _c-1

                  # remove other openings and closings in word range
                  while opens and opens[0] <= c:
                    opens.pop(0)
                    closes.pop(0)
                  askProtect = False

              # apply/dont apply protection
              protect = v[o+1:c]
              if (protect.strip()
                    and all([_c not in v[:c] for _c in r'\/:_&'])):
                if shouldBeProtected(v, v[o+1:c].replace('{', '').replace('}', ''),
                                     askProtect=askProtect):
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
            while True:
              i = v.find(protect, i+1)
              if i < 0:
                break
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

    res = f'@{self.section}{{{self.key}'+fieldsStr+'}'
    #io.dbg('pretty printed citation:', res)

    return res

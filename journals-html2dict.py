#!/usr/bin/env python3
import re

print('{')
for m in re.finditer(r'<td[^>]*>([^<>]*)<br[^>]*>([^<>]*)</td[^>]*>',
                     open('journals.html').read()):
  abbr, name = m.groups()[0].strip(), m.groups()[1].strip()
  print(f'  {repr(abbr)}: {repr(name)},')
print('}')

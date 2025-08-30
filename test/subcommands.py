import unittest
import subprocess
import os
import sys

# context that redirects stdout to /dev/null
class MuteStdout():
  def __enter__(self):
    self.stdout = sys.stdout
    sys.stdout.flush()
    sys.stdout = open(os.devnull, 'w')

  def __exit__(self, exc_type, exc_value, traceback):
    sys.stdout.close()
    sys.stdout = self.stdout


class TestSubcommands(unittest.TestCase):
  def _call(self, sub, *args):
    import paperman.__main__
    sys.argv = ['paperman', sub, *args]
    with MuteStdout():
      paperman.__main__.main()

  def test_bib(self):
    self._call('bib')

  def test_collect(self):
    self._call('collect')

  def test_diff(self):
    pass
    #self._call('diff')

  def test_img(self):
    self._call('img')

  def test_input(self):
    self._call('input')

  def test_journal(self):
    self._call('journal')

  def test_lib(self):
    pass
    #self._call('lib')

  def test_lint(self):
    self._call('lint')

  def test_sort_autors(self):
    self._call('sort-authors', 'max muster', 'moritz beispiel')


if __name__ == '__main__':
  unittest.main()

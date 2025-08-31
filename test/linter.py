import unittest
import subprocess
import os
import sys
from io import StringIO

# capture all content printed to stdout
class CaptureStdout(list):
  def __enter__(self):
    self._stdout = sys.stdout
    sys.stdout = StringIO()
    return self
  def __exit__(self, *args):
    self.extend(sys.stdout.getvalue().splitlines())
    sys.stdout = self._stdout

class TestMain(unittest.TestCase):
  def _call(self, sub, *args):
    import paperman.__main__
    sys.argv = ['paperman', sub, *args]
    with CaptureStdout() as res:
      paperman.__main__.main()
    return '\n'.join(res)

  def test_lint_example(self):
    res = self._call('lint', 'lint-example.tex')
    self.assertIn('found duplicate word "the"', res)
    self.assertIn('found duplicate word "a"', res)
    self.assertIn(r'found latex command \ref, which is on avoid-list', res)
    self.assertIn('math should be wrapped in curly braces to avoid', res)
    self.assertIn('', res)
    self.assertIn('', res)
    self.assertIn('', res)
    self.assertIn('', res)
    self.assertIn('', res)
    self.assertIn('', res)
    self.assertIn('', res)
    self.assertIn('', res)
    self.assertIn('', res)
    

if __name__ == '__main__':
  unittest.main()

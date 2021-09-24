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


class TestMain(unittest.TestCase):
  def test_main(self):
    import paperman.__main__
    sys.argv = ['paperman', '--version']
    with MuteStdout():
      paperman.__main__.main()


if __name__ == '__main__':
  unittest.main()

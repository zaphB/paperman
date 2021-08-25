from . import io
from . import cfg
from . import utils


@utils.logExceptionsAndRaise
def main():
  # show startup message
  io.startup()

  # raise error if required config keys are missing
  cfg.testIfRequiredExist()


if __name__ == '__main__':
  main()

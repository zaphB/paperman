# PYTHON_ARGCOMPLETE_OK

import argcomplete
import argparse

from . import io
from . import cfg
from . import utils


@utils.logExceptionsAndRaise
def main():
  # show startup message
  io.startup()

  # setup argparser and global arguments
  p = argparse.ArgumentParser()
  p.add_argument('-v', '--verbose', action='store_true',
                 help='print more detailed output')

  sub = p.add_subparsers(metavar='subcommands', dest='command', required=True)

  # options used by multiple subparsers
  def addTexFileArg(parser):
    parser.add_argument('tex_file', default='', nargs='?',
                        help='toplevel tex file of the document')

  # img command
  s = sub.add_parser('img', help='image helper: check if unused images exist '
                                 'or import missing images')
  addTexFileArg(s)
  s.add_argument('-i', '--import', action='store_true',
                 help='try importing missing images from image library')

  # bib command
  s = sub.add_parser('bib', help='bibliography helper: check if unused bib '
                                 'entries exist or import missing entries')
  addTexFileArg(s)

  # sort authors command
  s = sub.add_parser('sort-authors',
                     help='alphabetic sorting and formatting of author lists '
                          'for scientific publications and presentations')
  s.add_argument('authors', nargs='+',
                 help='comma separated list of authors seperated. Use -s '
                      'option for a different separator')
  s.add_argument('-s', '--separator', default=',',
                 help='separation character in author list')
  s.add_argument('-f', '--full-name', action='store_true',
                 help='output full author names.')
  s.add_argument('--keep-first', action='store_true',
                 help='keep position of first author in list.')
  s.add_argument('--keep-last', action='store_true',
                 help='keep position of last author in list.')
  s.add_argument('-k', '--keep-first-and-last', action='store_true',
                 help='keep position of first and last author in list.')
  s.add_argument('-q', '--quiet', action='store_true',
                 help='just output the sorted author list, nothing else.')
  s.add_argument('--no-and', action='store_true',
                 help='use the separator instead of "and" before the final '
                      'name and ignore ands in input.')

  # enable autocompletion and parse args
  argcomplete.autocomplete(p)
  args = p.parse_args()

  # apply verbosity setting
  io.isVerbose = args.verbose

  # select submodule for subcommands
  if args.command == 'img':
    from .subcommands import img as cmd

  elif args.command == 'bib':
    from .subcommands import bib as cmd

  elif args.command == 'sort-authors':
    from .subcommands import sort_authors as cmd

  else:
    io.dbg(f'{args=}')
    raise ValueError(f'args.command has unexpected value')


  # raise error if required config keys are missing
  cfg.testIfRequiredExist()

  # run subcommand module
  if cmd:
    try:
      cmd.main(args)
    except KeyboardInterrupt:
      raise
    except RuntimeError as e:
      io.err(str(e))
    except Exception as e:
      if cfg.get('debug'):
        raise
      io.err(str(e))


if __name__ == '__main__':
  main()

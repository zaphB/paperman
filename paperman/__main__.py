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

  # options used by multiple subparsers
  def addVerboseArg(parser):
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='print more detailed output')
  def addTexFileArg(parser):
    parser.add_argument('tex_file', default='', nargs='?',
                        help='toplevel tex file of the document')

  # setup argparser and global arguments
  p = argparse.ArgumentParser()
  addVerboseArg(p)
  p.add_argument('--version', action='store_true',
                 help='print installed paperman version')

  sub = p.add_subparsers(metavar='subcommands', dest='command')

  # img command
  s = sub.add_parser('img', help='image helper: check if unused or missing '
                                 'images exist or import missing images')
  addTexFileArg(s)
  addVerboseArg(s)
  s.add_argument('-i', '--import', action='store_true',
                 help='try importing missing images from image search path')
  s.add_argument('-c', '--clean', action='store_true',
                 help='remove unused images')

  # bib command
  s = sub.add_parser('bib', help='bibliography helper: check if unused or '
                                 'missing bib entries exist or import '
                                 'missing entries')
  addTexFileArg(s)
  addVerboseArg(s)
  s.add_argument('-p', '--print', action='store_true',
                 help='try to find missing citations in existing bibliographies '
                      'and show them in the shell, conflicts with --import, '
                      '--rewrite, and --sort')
  s.add_argument('-i', '--import', action='store_true',
                 help='try importing missing citations from existing '
                      'bibliographies')
  s.add_argument('-c', '--clean', action='store_true',
                 help='remove unused citations from bibliography, implies '
                      '--rewrite')
  s.add_argument('-r', '--rewrite', action='store_true',
                 help='rewrite and repair entire bibliography')
  s.add_argument('-s', '--sort', nargs='?', default=False,
                 help='sort bibliography, sort order can be one of "date", '
                      '"author" or "key", default is "key", implies --rewrite')

  # input command
  s = sub.add_parser('input',
                     help=r'input helper: check if all \input{} files exist '
                          r'or import files')
  addTexFileArg(s)
  addVerboseArg(s)
  s.add_argument('-i', '--import', action='store_true',
                 help=r'try importing missing \input{} files from input '
                      r'search path')

  # call img, bib and input command with --import flag set
  s = sub.add_parser('import-all',
                     help='shortcut to run img, bib and input subcommands '
                          'with --import option enabled')
  addTexFileArg(s)
  addVerboseArg(s)

  # sort authors command
  s = sub.add_parser('sort-authors',
                     help='alphabetic sorting and formatting of author lists '
                          'for scientific publications and presentations')
  addVerboseArg(s)
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

  # collect bib/pdf pairs from specified collect directories
  s = sub.add_parser('collect',
                     help='rename and move bib-pdf file pairs from specified '
                          'folders to library')
  addVerboseArg(s)
  s.add_argument('paths', nargs='*',
                 help='specify paths to import bib-pdf file pairs from, '
                      'defaults to paths given in config')
  s.add_argument('-w', '--watch', action='store_true',
                 help='never exit and keep watching the collect directories')
  s.add_argument('-e', '--err-to-file', action='store_true',
                 help='write errors not only to stdout, but also to a txt file '
                      'located in the same position as the bib-pdf file pair '
                      'that caused the error')

  # library subcommand
  s = sub.add_parser('lib',
                     help='search library, check library health, detect '
                          'corrupt bib files, duplicates and possibly '
                          'broken pdfs')
  addVerboseArg(s)
  s.add_argument('-f', '--find', nargs='+',
                 help='find library entries that contain given words in '
                      'bibtex fields')
  s.add_argument('-F', '--find-fulltext', nargs='+',
                 help='find library entries that contain given words in '
                      'full manuscript text (requires pdf2txt program to '
                      'to be installed on your $PATH)')
  s.add_argument('-k', '--key', action='store_true',
                 help='print citation key instead of path')
  s.add_argument('-l', '--long', action='store_true',
                 help='print full bibtex entries instead of path only')
  #s.add_argument('-L', '--extra-long', action='store_true',
  #               help='print full pdf2txt result instead of path only')

  # sync subcommand
  s = sub.add_parser('sync',
                     help='sync library pdfs to a tablet or other device')
  addVerboseArg(s)
  s.add_argument('-p', '--sync-path',
                 help='path to the device root that is to be synced.')

  # diff subcommand
  s = sub.add_parser('diff',
                     help='build pdfs that show changes between file versions')
  addVerboseArg(s)
  s.add_argument('-t' , '--old-is-tag', action='store_true',
                 help='do not treat "old" argument as filename, '
                      'but as git tag name (requires git to be installed '
                      'in your $PATH, requires current directory to be '
                      'git repository)')
  s.add_argument('-T' , '--new-is-tag', action='store_true',
                 help='do not treat "new" argument as filename, '
                      'but as git tag name (requires git to be installed '
                      'in your $PATH, requires current directory to be '
                      'git repository)')
  s.add_argument('-o', '--outfile', nargs='?', default='diff.pdf',
                 help='name of the pdf file to be built')
  s.add_argument('-k', '--keep', action='store_true',
                 help='keep build files build files')
  s.add_argument('-c', '--clean', action='store_true',
                 help='remove all build files except for output pdf')
  s.add_argument('old', help='filename of old version')
  s.add_argument('new', help='filename of new version')
  s.add_argument('filename', nargs='?',
                 help='only used if both --old-is-tag and '
                      '--new-is-tag are set, specifies filename')

  # make-diff subcommand
  s = sub.add_parser('journal',
                     help='find full journal names and abbreviations')
  addVerboseArg(s)
  s.add_argument('-f', '--full', action='store_true',
                 help='print full names of found journals')
  s.add_argument('-a', '--abbreviated', action='store_true',
                 help='print abbreviated names of found journals ')
  s.add_argument('--list-suspicious', action='store_true',
                 help='print all journals in database that might by errornous, '
                      'i.e., abbreviations that do not end with a dot')
  s.add_argument('name', nargs='*',
                 help='journal name, abbreviation or partial name')

  # lint subcommand
  s = sub.add_parser('lint',
                     help='search latex project for potential errors')
  addVerboseArg(s)
  addTexFileArg(s)

  # clean subcommand
  s = sub.add_parser('clean',
                     help='recurse into subfolders of current directory and '
                          'remove latex build files')
  addVerboseArg(s)

  # config subcommand
  s = sub.add_parser('config',
                     help='print location of config file and exit')
  s.add_argument('-o', '--open', action='store_true',
                 help='open config file in vim')
  addVerboseArg(s)

  # enable autocompletion and parse args
  argcomplete.autocomplete(p)
  args = p.parse_args()

  # apply verbosity setting
  io.isVerbose = args.verbose

  # if version is requested, print version and exit
  if args.version:
    io.info(f'paperman version {io.__version__}')
    return

  # select submodule for subcommands
  cmd, cmds = None, None
  if not args.command:
    io.err('subcommand is required')
    return

  elif args.command == 'img':
    from .subcommands import img as cmd

  elif args.command == 'bib':
    from .subcommands import bib as cmd

  elif args.command == 'input':
    from .subcommands import inp as cmd

  elif args.command == 'import-all':
    from .subcommands import inp as cmd1
    from .subcommands import img as cmd2
    from .subcommands import bib as cmd3
    setattr(args, 'import', True)
    args.clean = False
    args.rewrite = False
    args.sort = False
    args.print = False
    cmds = [cmd1, cmd2, cmd3]

  elif args.command == 'sort-authors':
    from .subcommands import sort_authors as cmd

  elif args.command == 'collect':
    from .subcommands import collect as cmd

  elif args.command == 'lib':
    from .subcommands import lib as cmd

  elif args.command == 'sync':
    from .subcommands import sync as cmd

  elif args.command == 'diff':
    from .subcommands import diff as cmd

  elif args.command == 'journal':
    from .subcommands import journal as cmd

  elif args.command == 'lint':
    from .subcommands import lint as cmd

  elif args.command == 'clean':
    from .subcommands import clean as cmd

  elif args.command == 'config':
    from .subcommands import config as cmd

  else:
    io.dbg(f'args={args}')
    raise ValueError(f'args.command has unexpected value')


  # raise error if required config keys are missing
  cfg.testIfRequiredExist()

  # run subcommand module
  cmdStr = str(cmd or '\n'+'\n'.join([str(c) for c in cmds]))
  io.verb(f'selected subcommand(s): {cmdStr}')
  try:
    if cmd:
      cmds = [cmd]
    if cmds:
      for cmd in cmds:
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

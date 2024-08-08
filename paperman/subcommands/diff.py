import shutil
import subprocess

from .. import utils
from .common import *


def main(args):
  buildDir = '.'
  if args.old_is_tag and args.new_is_tag:
    buildDir = os.path.dirname(args.filename)
  elif args.old_is_tag:
    buildDir = os.path.dirname(args.new)
  elif args.new_is_tag:
    buildDir = os.path.dirname(args.old)
  else:
    buildDir = os.path.dirname(args.new)
  buildDir = buildDir or '.'

  # if clean option is set, just clean and return
  if args.clean:
    for f in os.listdir(buildDir):
      if f.startswith('paperman-diff'):
        fname = os.path.join(buildDir, f)
        os.remove(fname)
        io.verb(f'removing {fname}')
    return

  # check if build files exist and warn about
  # overwriting them
  if any([f.startswith('paperman-diff') for f in os.listdir(buildDir)]):
    if not io.conf(f'filenames beginning with "paperman-diff" exist',
                   f'in "{(buildDir or ".")+os.path.sep}" and may be overwritten',
                   f'during diff build, continue?', default=True):
      return

  # function to copy file versions
  def copyToBuildDir(path, name, buildDir=buildDir):
    texSrc = utils.replaceSuffix(path, 'tex')
    texTar = os.path.join(buildDir, name+'.tex')
    shutil.copy(texSrc, texTar)
    io.verb(f'copied {texSrc} -> {texTar}')

    bblSrc = utils.replaceSuffix(path, 'bbl')
    bblTar = os.path.join(buildDir, name+'.bbl')
    if os.path.exists(bblSrc):
      shutil.copy(bblSrc, bblTar)
      io.verb(f'copied {bblSrc} -> {bblTar}')
    elif os.path.exists(bblTar):
      os.remove(bblTar)
      io.verb(f'removed {bblTar}')

  # function to extract tagged file versions
  def gitShowToBuildDir(tag, path, name):
    texPath = utils.replaceSuffix(path, 'tex')
    r = subprocess.run(['git', 'show', tag+':./'+texPath],
                       capture_output=True)
    if r.returncode:
      raise RuntimeError('failed to get tex file via "git show":\n'
                         +r.stdout.decode()+'\n'+r.stderr.decode())
    texTar = os.path.join(buildDir, name+'.tex')
    with open(texTar, 'w') as f:
      f.write(r.stdout.decode())
    io.verb(f'wrote result of "git show {tag}:./{texPath}" to {texTar}')

    bblPath = utils.replaceSuffix(path, 'bbl')
    bblTar = os.path.join(buildDir, name+'.bbl')
    r = subprocess.run(['git', 'show', tag+':./'+bblPath], capture_output=True)
    if r.returncode:
      io.warn('failed to get bbl file via "git show":\n'
              +r.stdout.decode()+'\n'+r.stderr.decode())
      if os.path.exists(bblTar):
        os.remove(bblTar)
        io.verb(f'removed {bblTar}')
    else:
      bblTar = os.path.join(buildDir, name+'.bbl')
      with open(bblTar, 'w') as f:
        f.write(r.stdout.decode())
      io.verb(f'wrote result of "git show {tag}:./{bblPath}" to {bblTar}')

  # prepare old files
  if args.old_is_tag:
    if args.new_is_tag:
      path = args.filename
    else:
      path = args.new
    gitShowToBuildDir(args.old, path, 'paperman-diff-old')
  else:
    copyToBuildDir(args.old, 'paperman-diff-old')

  # prepare new files
  if args.new_is_tag:
    if args.old_is_tag:
      path = args.filename
    else:
      path = args.old
    gitShowToBuildDir(args.new, path, 'paperman-diff-new')
  else:
    copyToBuildDir(args.new, 'paperman-diff-new')

  # run command and raise on error
  def run(*cmd, stdout=None, raiseOnErr=True):
    io.verb('running command: '+' '.join(cmd))
    r = subprocess.run(cmd, cwd=buildDir,
                       stderr=subprocess.PIPE,
                       stdout=stdout or subprocess.PIPE)
    if r.returncode:
      io.verb(f'command failed: {r.returncode}')
      if raiseOnErr:
        raise RuntimeError(f'{cmd[0]} failed unexpectedly\n'
                          +r.stdout.decode()+'\n'+r.stderr.decode())
      else:
        return False
    io.verb(f'command exited successful')
    return r

  # run build process
  target = os.path.join(buildDir, 'paperman-diff.pdf')
  if os.path.exists(target):
    os.remove(target)
    io.verb(f'removed {target}')

  for fs, msg in ([True, 'trying to build with -t FLOATSAFE...'],
                  [False, 'trying to build without -t FLOATSAFE...']):
  #                [None, 'trying to build without bib-diff...']):
    io.info(msg)
    for e in ('tex', 'bbl'):
      bblOld = os.path.join(buildDir, 'paperman-diff-old.bbl')
      bblNew = os.path.join(buildDir, 'paperman-diff-new.bbl')
      if (e == 'bbl'
            and (not os.path.exists(bblOld)
               or not os.path.exists(bblNew)
               or fs is None)):
        bblTar = os.path.join(buildDir, 'paperman-diff.bbl')
        if os.path.exists(bblNew):
          shutil.copy(bblNew, bblTar)
          io.verb(f'copied {bblNew} -> {bblTar}')

        elif os.path.exists(bblOld):
          shutil.copy(bblOld, bblTar)
          io.verb(f'copied {bblOld} -> {bblTar}')

        continue

      with open(os.path.join(buildDir, 'paperman-diff.'+e), 'w') as f:
        run('latexdiff', *(['-t', 'FLOATSAFE'] if e=='tex' and fs else []),
            'paperman-diff-old.'+e, 'paperman-diff-new.'+e, stdout=f)

    for _ in range(2):
      res = run('pdflatex', '-interaction=nonstopmode', 'paperman-diff',
                raiseOnErr=False) #not fs) #fs is None)

    # if successful, break
    if res:
      break

  if os.path.exists(target):
    shutil.move(os.path.join(buildDir, 'paperman-diff.pdf'), args.outfile)

    # remove build files if 'keep' flag is not set
    if not args.keep:
      for f in os.listdir(buildDir):
        if f.startswith('paperman-diff'):
          fname = os.path.join(buildDir, f)
          os.remove(fname)
          io.verb(f'removed {fname}')

    io.info(f'successfully generated {args.outfile}')
  else:
    io.err('failed to build diff')

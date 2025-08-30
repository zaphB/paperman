import subprocess
import shutil
import time

from .common import *

def main(args):
  # extract sync path from config or from argument list
  if args.sync_path:
    syncPath = args.sync_path
  else:
    syncPath = os.path.expanduser(cfg.get('library_sync_device'))
  if not syncPath:
    io.err('library_sync_device config is not set up')
    return

  # clean path
  while syncPath.endswith('/'):
    syncPath = syncPath[:-1]

  # test if sync path is among mounted paths
  mounts = subprocess.run(['mount'], capture_output=True).stdout.decode()
  if syncPath not in mounts:
    io.err(f'sync device at {syncPath} does not seem to be mounted')
    return

  # try to place busy file
  try:
    with open(syncPath+'/paperman-sync-busy', 'w') as f:
      pass
  except KeyboardInterrupt:
    raise
  except:
    io.err(f'failed to place busy file at {syncPath}, do you have write access?')
    return

  # init flag
  nothingDone = True

  # walk through library pdfs and upload missing ones
  libPath = os.path.expanduser(cfg.get('library_path'))
  additionalPaths = [os.path.expanduser(p) for p in cfg.get('library_sync_additional_paths')]
  for _path in [libPath]+additionalPaths:
    for root, dirs, files in os.walk(_path, topdown=True):
      dirs[:] = [d for d in dirs if not d.startswith('.')]
      files[:] = [f for f in files if not f.startswith('.')]

      for f in files:
        if _path == libPath:
          relPath = root[len(_path):]
        else:
          relPath = root[_path.rfind('/')+1:]
        if relPath.startswith('/'):
          relPath = relPath[1:]

        if f.endswith('.pdf') and not relPath.startswith('annotated'):

          # check if file looks valid and is not too old
          s = os.stat(root+'/'+f)
          if (s.st_size > 0 and
              time.time()-s.st_mtime < cfg.get('library_sync_max_age')):

            # create target path
            target = f'{syncPath}/{relPath}/{f}'
            if not os.path.exists(target):
              io.info(f'uploading {relPath}/{f}')
              os.makedirs(os.path.dirname(target), exist_ok=True)
              shutil.copy(root+'/'+f, target)
              nothingDone = False

  # copying files that changed on the device to annotated folder
  for root, dirs, files in os.walk(syncPath, topdown=True):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    files[:] = [f for f in files if not f.startswith('.')]

    for f in files:
      # check if file also exists in library but has different size
      relPath = root[len(syncPath):]
      if relPath.startswith('/'):
        relPath = relPath[1:]

      if f.endswith('.pdf'):
        # skip folder names beginning with a dot
        if not relPath.startswith('.'):

          # go through all possible local path candidates, if any of them
          # exists and has the same file size, do not copy it
          localCandidates = ([f'{libPath}/{relPath}/{f}']
                            +[f'{_p[:_p.rfind("/")]}/{relPath}/{f}'
                                                  for _p in additionalPaths])
          if not any([os.path.exists(l)
                        and os.stat(l).st_size == os.stat(root+'/'+f).st_size
                                for l in localCandidates]):

            # create target path, if it exists, modify target path
            # and copy only if size of existing file differs
            target = f'{libPath}/annotated/{relPath}/{f}'
            origTarget = target
            existing = None
            i = 0
            while os.path.exists(target):
              i += 1
              existing = target
              target = ('.'.join(origTarget.split('.')[:-1])
                            +f'-v{i:02d}.'
                            +origTarget.split('.')[-1])

            # copy file only if last version of annotated file has different
            # size than current version of annotated file (or if target does
            # not exist)
            if (existing is None or
                  os.stat(existing).st_size != os.stat(root+'/'+f).st_size):
              io.info(f'downloading annotated {relPath}/{f}')
              os.makedirs(os.path.dirname(target), exist_ok=True)
              shutil.copy(root+'/'+f, target)
              nothingDone = False

  # indicate that something happened even if nothing was copied
  if nothingDone:
    io.info('nothing to do')

  # remove busy file
  os.remove(syncPath+'/paperman-sync-busy')

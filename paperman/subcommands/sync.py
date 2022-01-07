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
  for root, dirs, files in os.walk(libPath):
    for f in files:
      relPath = root[len(libPath):]
      if relPath.startswith('/'):
        relPath = relPath[1:]

      if f.endswith('.pdf') and not relPath.startswith('annotated'):

        # check if file looks valid is not too old
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
  for root, dirs, files in os.walk(syncPath):
    for f in files:
      # check if file also exists in library but has different size
      relPath = root[len(syncPath):]
      if relPath.startswith('/'):
        relPath = relPath[1:]

      if f.endswith('.pdf'):
        local = f'{libPath}/{relPath}/{f}'

        # consider copy if file doesn ot exist locally or if sizes differ,
        # skip folder names beginning with a dot
        if (not relPath.startswith('.')
              and (not os.path.exists(local)
                 or os.stat(local).st_size != os.stat(f'{root}/{f}').st_size)):

          # create target path and copy if target does not exist or has
          # different size
          target = f'{libPath}/annotated/{relPath}/{f}'
          if (not os.path.exists(target) or
                os.stat(target).st_size != os.stat(root+'/'+f).st_size):
            io.info(f'downloading annotated {relPath}/{f}')
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy(root+'/'+f, target)
            nothingDone = False

  # indicate that something happened even if nothing was copied
  if nothingDone:
    io.info('nothing to do')

  # remove busy file
  os.remove(syncPath+'/paperman-sync-busy')

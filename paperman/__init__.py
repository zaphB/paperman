from . import io
from . import cfg
from . import utils


# try to extract version info
try:
  import importlib.metadata
  __version__ = importlib.metadata.version('paperman')
except:
  try:
    import pkg_resources
    __version__ = pkg_resources.get_distribution('paperman').version
  except:
    __version__ = '???'

# set version attribute for submodules that need it
for m in [io, ]:
  m.__version__ = __version__

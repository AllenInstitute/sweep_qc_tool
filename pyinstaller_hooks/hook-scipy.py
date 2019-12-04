import os

import scipy

scipy_dir = os.path.dirname(scipy.__file__)
scipy_dll_glob = os.path.join(scipy_dir, ".libs", "*.dll")

binaries = [(scipy_dll_glob, "dlls")]
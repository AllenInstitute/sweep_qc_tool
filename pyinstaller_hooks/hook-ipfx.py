import os

import ipfx

ipfx_dir = os.path.dirname(ipfx.__file__)
defaults_glob = os.path.join(ipfx_dir, "defaults", "*")
defaults_dir = os.path.join("ipfx", "defaults")

# borrowing this temporarily from @kasbaker's c803fbf71f1c7233b3d9ec128e586fd8bc4d3a66
version_file = os.path.join(ipfx_dir, "version.txt")
version_dir = os.path.join("ipfx")

datas = [(defaults_glob, defaults_dir), (version_file, version_dir)]
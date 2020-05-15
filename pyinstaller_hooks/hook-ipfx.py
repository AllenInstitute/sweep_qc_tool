import os

import ipfx

ipfx_dir = os.path.dirname(ipfx.__file__)
defaults_glob = os.path.join(ipfx_dir, "defaults", "*")
defaults_dir = os.path.join("ipfx", "defaults")

version_file = os.path.join(ipfx_dir, "version.txt")
version_dir = os.path.join("ipfx")

datas = [(defaults_glob, defaults_dir), (version_file, version_dir)]

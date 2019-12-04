import os

import ipfx

ipfx_dir = os.path.dirname(ipfx.__file__)
defaults_glob = os.path.join(ipfx_dir, "defaults", "*")
defaults_dir = os.path.join("ipfx", "defaults")

datas = [(defaults_glob, defaults_dir)]
import os

import pynwb

pynwb_dir = os.path.dirname(pynwb.__file__)
spec_glob = os.path.join(pynwb_dir, "data", "*.yaml")
spec_dir = os.path.join("pynwb", "data")

datas = [(spec_glob, spec_dir)]
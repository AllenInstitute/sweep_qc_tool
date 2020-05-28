import os

import pynwb

pynwb_dir = os.path.dirname(pynwb.__file__)
spec_dir = os.path.join(pynwb_dir, "nwb-schema", "core")
spec_glob = os.path.join(spec_dir, "*.yaml")

datas = [(spec_glob, spec_dir)]
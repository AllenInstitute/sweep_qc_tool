import os

import pynwb

hdmf_dir = os.path.dirname(hdmf.__file__)
spec_dir = os.path.join(hdmf_dir, "common", "hdmf-common-schema")
spec_glob = os.path.join(spec_dir, "*.yaml")

datas = [(spec_glob, spec_dir)]
import os

import hdmf

hdmf_dir = os.path.dirname(hdmf.__file__)
spec_dir = os.path.join("hdmf", "common", "hdmf-common-schema", "common")
spec_glob = os.path.join(hdmf_dir, "common", "hdmf-common-schema", "common", "*.yaml")

datas = [(spec_glob, spec_dir)]
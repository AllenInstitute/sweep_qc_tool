import os
import opcode


def pre_find_module_path(pfmp_api):
    """ When freezing from virtualenv, pyinstaller finds the virtualenv version of 
    distutils, which is not suitable for use outside of a virtualenv. This causes the
    system virtualenv to be found instead.

    See https://github.com/pyinstaller/pyinstaller/issues/4064 for more information and several 
    viable solutions.
    """

    # this trick comes from virtualenv:
    # https://github.com/pypa/virtualenv/blob/591282f224d5d128f4452a319e0ed9a3bcb058c1/virtualenv_embedded/distutils-init.py#L5
    # we can use a non-virtualenv module (opcode) to find the system distutils
    system_distutils_path = os.path.normpath(
        os.path.join(
            os.path.dirname(opcode.__file__), 
            "distutils"
        )
    )

    # Then we tell the pre-find-module-path api to look there first
    pfmp_api.search_dirs = [system_distutils_path] + pfmp_api.search_dirs
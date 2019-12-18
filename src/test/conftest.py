

# Making this app's source code a package breaks the windows freeze, so 
# we'll get imports via path munging
import sys
import os

import pytest_check as check

import numpy as np

sys.path.append(os.path.join(
    os.path.dirname(
        os.path.dirname(__file__)
    ),
    "main",
    "python"
))


@check.check_func
def allclose(a, b, *args, **kwargs):
    assert np.allclose(a, b, *args, **kwargs)


@check.check_func
def mock_called_with(mc, *args, **kwargs):
    mc.assert_called_with(*args, **kwargs)


@check.check_func
def mock_not_called(mc):
    mc.assert_not_called()
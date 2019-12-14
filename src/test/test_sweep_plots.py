import pytest

import numpy as np

from sweep_plotter import test_response_plot_data


class MockSweep:

    @property
    def t(self):
        return np.arange(0, 10, 0.5)
    
    @property
    def v(self):
        return np.arange(0, 10, 0.5)


@pytest.fixture
def sweep():
    return MockSweep()

    
@pytest.mark.parametrize("start,end,baseline,expected", [
    [2.0, 5.0, 3, ([2, 2.5, 3, 3.5, 4, 4.5], [1.5, 2, 2.5, 3, 3.5, 4])]
])
def test_test_response_plot_data(sweep, start, end, baseline, expected):

    obtained = test_response_plot_data(sweep, start, end, baseline)
    assert np.allclose(expected[0], obtained[0])
    assert np.allclose(expected[1], obtained[1])
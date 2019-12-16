import pytest

import numpy as np

from sweep_plotter import (
    test_response_plot_data, 
    TestPopupPlotter, ExperimentPopupPlotter
)


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


@pytest.mark.parametrize("time,voltage,previous,initial,sweep_number", [
    [np.arange(20), np.arange(20), None, None, 40],
    [np.arange(20), np.arange(20), np.arange(20) * 2, np.arange(20) * 3, 40]

])
def test_test_popup_plotter(time,voltage,previous,initial,sweep_number):

    plotter = TestPopupPlotter(time, voltage, previous, initial, sweep_number)
    graph = plotter()

    data_items = graph.getPlotItem().listDataItems()
    assert len(data_items) == 3 - (previous is None) - (initial is None)

    for item in data_items:
        assert np.allclose(item.xData, time)

        if item.name == f"sweep {sweep_number}":
            assert np.allclose(item.yData, voltage)
        elif item.name == "previous":
            assert np.allclose(item.yData, previous) 
        elif item.name == "initial":
            assert np.allclose(item.yData, initial) 

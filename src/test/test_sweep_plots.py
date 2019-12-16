import pytest
import pytest_check as check

import numpy as np
from pyqtgraph import InfiniteLine

from sweep_plotter import (
    test_response_plot_data, 
    PulsePopupPlotter, ExperimentPopupPlotter
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


@check.check_func
def allclose(a, b, *args, **kwargs):
    assert np.allclose(a, b, *args, **kwargs)

    
@pytest.mark.parametrize("start,end,baseline,expected", [
    [2.0, 5.0, 3, ([2, 2.5, 3, 3.5, 4, 4.5], [1.5, 2, 2.5, 3, 3.5, 4])]
])
def test_test_response_plot_data(sweep, start, end, baseline, expected):

    obtained = test_response_plot_data(sweep, start, end, baseline)
    allclose(expected[0], obtained[0])
    allclose(expected[1], obtained[1])


@pytest.mark.parametrize("time,voltage,previous,initial,sweep_number", [
    [np.arange(20), np.arange(20), None, None, 40],
    [np.arange(20), np.arange(20), np.arange(20) * 2, np.arange(20) * 3, 40]

])
def test_pulse_popup_plotter(time, voltage, previous, initial, sweep_number):

    plotter = PulsePopupPlotter(time, voltage, previous, initial, sweep_number)
    graph = plotter()

    data_items = graph.getPlotItem().listDataItems()
    check.equal(len(data_items), 3 - (previous is None) - (initial is None))

    for item in data_items:
        allclose(item.xData, time)

        if item.name == f"sweep {sweep_number}":
            allclose(item.yData, voltage)
        elif item.name == "previous":
            allclose(item.yData, previous) 
        elif item.name == "initial":
            allclose(item.yData, initial)


@pytest.mark.parametrize("time,voltage,baseline", [
    [np.linspace(0, np.pi, 20), np.arange(20), 1.0]
])
def test_experiment_popup_plotter_graph(time, voltage, baseline):

    plotter = ExperimentPopupPlotter(time, voltage, baseline)
    graph = plotter()

    data_items = graph.getPlotItem().listDataItems()
    
    check.equal(len(data_items), 1)
    allclose(data_items[0].xData, time)
    allclose(data_items[0].yData, voltage)

    line = None
    for item in graph.getPlotItem().items:
        if isinstance(item, InfiniteLine) and item.label.format == "baseline":
            line = item

    check.is_not_none(line)
    check.equal(line.y(), baseline)

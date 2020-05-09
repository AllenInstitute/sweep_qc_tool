import pytest
import pytest_check as check

import numpy as np
from pyqtgraph import InfiniteLine

from sweep_plotter import (
    test_response_plot_data, experiment_plot_data,
    PulsePopupPlotter, ExperimentPopupPlotter, PlotData
)

from .conftest import check_allclose


class MockSweep:
    """ A mock current clamp sweep. """
    def __init__(self, clamp_mode="CurrentClamp"):
        self._clamp_mode = clamp_mode

    @property
    def t(self):
        return np.arange(0, 10, 0.5)
    
    @property
    def v(self):
        return np.arange(0, 10, 0.5)

    @property
    def i(self):
        current = np.zeros(10)
        current[2:] += 1
        current[3:] -= 1
        current[6:] += 1
        current[-1] = 0
        return current

    @property
    def stimulus(self):
        if self.clamp_mode == "CurrentClamp":
            return self.i
        else:
            return self.v

    @property
    def response(self):
        if self.clamp_mode == "CurrentClamp":
            return self.v
        else:
            return self.i

    @property
    def sampling_rate(self):
        return 0.0

    @property
    def clamp_mode(self):
        return self._clamp_mode


class MockDataSet:
    @property
    def sweep_table(self):
        return [
            {'sweep_number': 0, 'stimulus_code': "foobar"},
            {'sweep_number': 1, 'stimulus_code': "fooSearch"},
            {'sweep_number': 2, 'stimulus_code': "NucVCbar"}
        ]

    def sweep(self, sweep_number):
        if sweep_number in (0, 1):
            return MockSweep(clamp_mode="CurrentClamp")
        elif sweep_number in 3:
            return MockSweep(clamp_mode="VoltageClamp")

@pytest.fixture
def sweep():
    return MockSweep(clamp_mode="CurrentClamp")

@pytest.mark.parametrize("start,end,baseline,expected", [
    [2.0, 5.0, 3, PlotData(
        stimulus=[0.0, 0.0, 1.0, 1.0, 1.0, 0.0],
        time=[2, 2.5, 3, 3.5, 4, 4.5],
        response=[1.5, 2, 2.5, 3, 3.5, 4],
    )]
])
def test_test_response_plot_data(sweep, start, end, baseline, expected):

    obtained = test_response_plot_data(sweep, start, end, baseline)
    check_allclose(expected[0], obtained[0])
    check_allclose(expected[1], obtained[1])


def test_experiment_plot_data(sweep):
    obt, obt_base = experiment_plot_data(
        sweep, baseline_start_index=0, baseline_end_index=2
    )
    obt_t = obt.time
    obt_v = obt.response

    check_allclose(obt_t, [3, 3.5])
    check_allclose(obt_v, [3, 3.5])
    check.equal(obt_base, 3.25)


@pytest.mark.parametrize(
    "plot_data,previous_plot_data,initial_plot_data,sweep_number,y_label", [
        [PlotData(time=np.arange(20), response=np.arange(20), stimulus=np.arange(20)),
         None, None, 40, 'foo'],
        [PlotData(time=np.arange(20), response=np.arange(20), stimulus=np.arange(20)),
         PlotData(time=np.arange(20), response=np.arange(20)*2, stimulus=np.arange(20)),
         PlotData(time=np.arange(20), response=np.arange(20)*3, stimulus=np.arange(20)),
         40, 'foo']
    ])
def test_pulse_popup_plotter(
        plot_data, previous_plot_data, initial_plot_data, sweep_number, y_label
):

    plotter = PulsePopupPlotter(plot_data, previous_plot_data,
                                initial_plot_data, sweep_number, y_label)
    graph = plotter()

    data_items = graph.getPlotItem().listDataItems()
    check.equal(len(data_items), 3 - (previous_plot_data is None) - (initial_plot_data is None))

    for item in data_items:
        check_allclose(item.xData, plot_data.time)

        if item.name == f"sweep {sweep_number}":
            check_allclose(item.yData, plot_data.response)
        elif item.name == "previous":
            check_allclose(item.yData, previous_plot_data.response)
        elif item.name == "initial":
            check_allclose(item.yData, initial_plot_data.response)


@pytest.mark.parametrize("plot_data,baseline,sweep_number,y_label", [
    [PlotData(time=np.linspace(0, np.pi, 20), response=np.arange(20), stimulus=np.arange(20)),
     1.0, 40, 'foo']
])
def test_experiment_popup_plotter_graph(plot_data, baseline, sweep_number, y_label):

    plotter = ExperimentPopupPlotter(plot_data, baseline, sweep_number, y_label)
    graph = plotter()

    data_items = graph.getPlotItem().listDataItems()
    
    check.equal(len(data_items), 1)
    check_allclose(data_items[0].xData, plot_data.time)
    check_allclose(data_items[0].yData, plot_data.response)

    line = None
    for item in graph.getPlotItem().items:
        if isinstance(item, InfiniteLine) and item.label.format == "baseline":
            line = item

    check.is_not_none(line)
    check.equal(line.y(), baseline)

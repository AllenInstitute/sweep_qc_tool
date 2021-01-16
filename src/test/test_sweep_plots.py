import pytest
import pytest_check as check

import pandas as pd
import numpy as np
from pyqtgraph import InfiniteLine

from sweep_plotter import (
    SweepPlotConfig, PulsePopupPlotter, ExperimentPopupPlotter,
    PlotData, SweepPlotter
)

from .conftest import check_allclose

mock_config = SweepPlotConfig(
    test_pulse_plot_start=0.04,
    test_pulse_plot_end=0.1,
    test_pulse_baseline_samples=100,
    backup_experiment_start_index=5000,
    experiment_baseline_start_index=5000,
    experiment_baseline_end_index=9000,
    thumbnail_step=20
)


class MockSweep:
    """ A mock sweep """
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
    """ A mock data set """

    def __init__(self):
        self._sweep_table = None

    # noinspection PyTypeChecker
    @property
    def sweep_table(self):
        if self._sweep_table is None:
            self._sweep_table = pd.DataFrame([
                {'sweep_number': 0, 'stimulus_code': "EXTPSMOKET_bar", 'clamp_mode': "VoltageClamp"},
                {'sweep_number': 1, 'stimulus_code': "EXTPINBATH_bar", 'clamp_mode': "VoltageClamp"},
                {'sweep_number': 2, 'stimulus_code': "EXTPCllATT_bar", 'clamp_mode': "VoltageClamp"},
                {'sweep_number': 3, 'stimulus_code': "EXTPBREAKN_bar", 'clamp_mode': "VoltageClamp"},
                {'sweep_number': 4, 'stimulus_code': "foo", 'clamp_mode': "CurrentClamp"},
                {'sweep_number': 5, 'stimulus_code': "foo", 'clamp_mode': "CurrentClamp"},
                {'sweep_number': 6, 'stimulus_code': "fooSearch", 'clamp_mode': "CurrentClamp"},
                {'sweep_number': 7, 'stimulus_code': "bar", 'clamp_mode': "CurrentClamp"},
                {'sweep_number': 8, 'stimulus_code': "foobar", 'clamp_mode': "CurrentClamp"},
                {'sweep_number': 9, 'stimulus_code': "bat", 'clamp_mode': "CurrentClamp"},
                {'sweep_number': 10, 'stimulus_code': "fooRamp", 'clamp_mode': "CurrentClamp"},
                {'sweep_number': 11, 'stimulus_code': "EXTPGGAEND_bar", 'clamp_mode': "VoltageClamp"},
                {'sweep_number': 12, 'stimulus_code': "NucVCbat", 'clamp_mode': "VoltageClamp"},
                {'sweep_number': 13, 'stimulus_code': "NucVCbiz", 'clamp_mode': "VoltageClamp"},
                {'sweep_number': 14, 'stimulus_code': "NucVCfizz", 'clamp_mode': "VoltageClamp"}
            ])
            self._sweep_table.set_index('sweep_number')
        return self._sweep_table

    @property
    def sweep_numbers(self):
        return sorted(self.sweep_table['sweep_number'])

    def get_stimulus_code(self, sweep_number):
        return self.sweep_table.at[sweep_number, 'stimulus_code']

    def get_clamp_mode(self, sweep_number):
        return self.sweep_table.at[sweep_number, 'clamp_mode']

    def sweep(self, sweep_number):
        return MockSweep(clamp_mode=self.get_clamp_mode(sweep_number))


@pytest.fixture
def sweep():
    return MockSweep(clamp_mode="CurrentClamp")


@pytest.fixture
def mock_data_set():
    return MockDataSet()


@pytest.fixture
def mock_plotter(mock_data_set):
    stim_code_gen = (
        mock_data_set.get_stimulus_code(idx)
        for idx in mock_data_set.sweep_numbers  # this property is fastest
    )
    mock_sweep_dictionary = {
        idx: {'sweep': mock_data_set.sweep(idx), 'stimulus_code': stim_code}
        for idx, stim_code in enumerate(stim_code_gen)
        if "Search" not in stim_code  # these will not be plotted for speed
    }
    return SweepPlotter(sweep_dictionary=mock_sweep_dictionary, config=mock_config)


@pytest.mark.parametrize("start,end,baseline,expected", [
    [2.0, 5.0, 3, PlotData(
        stimulus=[0.0, 0.0, 1.0, 1.0, 1.0, 0.0],
        time=[2, 2.5, 3, 3.5, 4, 4.5],
        response=[1.5, 2, 2.5, 3, 3.5, 4],
    )]
])
def test_test_response_plot_data(mock_plotter, sweep, start, end, baseline, expected):

    obtained = mock_plotter.test_response_plot_data(sweep, start, end, baseline)
    check_allclose(expected[0], obtained[0])
    check_allclose(expected[1], obtained[1])


def test_experiment_plot_data(mock_plotter, sweep):
    obt, obt_base = mock_plotter.experiment_plot_data(
        sweep, baseline_start_index=0, baseline_end_index=2
    )
    obt_t = obt.time
    obt_r = obt.response

    check_allclose(obt_t, [3, 3.5])
    check_allclose(obt_r, [3, 3.5])
    check.equal(obt_base, 3.25)


@pytest.mark.parametrize(
    "plot_data,previous_plot_data,initial_plot_data,sweep_number,y_label,stimulus_code", [
        [PlotData(time=np.arange(20), response=np.arange(20), stimulus=np.arange(20)),
         None, None, 40, 'foo_label', 'foo_title'],
        [PlotData(time=np.arange(20), response=np.arange(20), stimulus=np.arange(20)),
         PlotData(time=np.arange(20), response=np.arange(20)*2, stimulus=np.arange(20)),
         PlotData(time=np.arange(20), response=np.arange(20)*3, stimulus=np.arange(20)),
         40, 'foo_label', 'foo_title']
    ])
def test_pulse_popup_plotter(
        plot_data, previous_plot_data, initial_plot_data,
        sweep_number, y_label, stimulus_code
):

    plotter = PulsePopupPlotter(
        plot_data, previous_plot_data, initial_plot_data,
        sweep_number, y_label, stimulus_code
    )

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


@pytest.mark.parametrize("plot_data,baseline,sweep_number,y_label,stimulus_code", [
    [PlotData(time=np.linspace(0, np.pi, 20), response=np.arange(20), stimulus=np.arange(20)),
     1.0, 40, 'foo_label', 'foo_title']
])
def test_experiment_popup_plotter_graph(
        plot_data, baseline, sweep_number, y_label, stimulus_code
):

    plotter = ExperimentPopupPlotter(
        plot_data, baseline, sweep_number, y_label, stimulus_code
    )
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


def test_advance(mock_plotter, mock_data_set):

    expected_stored_tp = {
        'initial_vclamp': None,
        'previous_vclamp': None,
        'initial_iclamp': None,
        'previous_iclamp': None,
    }

    for sweep_number in sorted(mock_plotter.sweep_dictionary.keys()):
        # determine if test pulse should be stored based on stimulus code
        stim_code = mock_data_set.get_stimulus_code(sweep_number)
        clamp_mode = mock_data_set.get_clamp_mode(sweep_number)

        # only store the test pulse if it is not in the list of excluded stim codes
        if not any(substring in stim_code for substring in mock_plotter.tp_exclude_codes):
            # record sweep numbers of expected stored test pulses for I clamp
            if clamp_mode == "CurrentClamp":
                if expected_stored_tp['initial_iclamp'] is None:
                    expected_stored_tp['initial_iclamp'] = sweep_number
                else:
                    expected_stored_tp['previous_iclamp'] = sweep_number
            # record sweep numbers of expected stored test pulses for V clamp
            else:
                if expected_stored_tp['initial_vclamp'] is None:
                    expected_stored_tp['initial_vclamp'] = sweep_number
                else:
                    expected_stored_tp['previous_vclamp'] = sweep_number

        mock_plotter.advance(sweep_number)
        # verify test pulses are stored properly
        if expected_stored_tp['initial_vclamp'] is None:
            assert mock_plotter.initial_vclamp_data is None
        else:
            assert mock_plotter.initial_vclamp_data is not None

        if expected_stored_tp['previous_vclamp'] is None:
            assert mock_plotter.previous_vclamp_data is None
        else:
            assert mock_plotter.previous_vclamp_data is not None

        if expected_stored_tp['initial_iclamp'] is None:
            assert mock_plotter.initial_iclamp_data is None
        else:
            assert mock_plotter.initial_iclamp_data is not None

        if expected_stored_tp['previous_iclamp'] is None:
            assert mock_plotter.previous_iclamp_data is None
        else:
            assert mock_plotter.previous_iclamp_data is not None

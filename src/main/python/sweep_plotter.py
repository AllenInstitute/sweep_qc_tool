import io

from typing import NamedTuple, Tuple, Union, Optional

from PyQt5.QtCore import QByteArray

from pyqtgraph import PlotWidget, mkPen

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import bessel, filtfilt

from ipfx.ephys_data_set import EphysDataSet
from ipfx.sweep import Sweep
from ipfx.epochs import get_experiment_epoch


PLOT_FONTSIZE = 24
DEFAULT_FIGSIZE = (8, 8)


class SweepPlotConfig(NamedTuple):
    test_pulse_plot_start: float
    test_pulse_plot_end: float
    test_pulse_baseline_samples: int
    backup_experiment_start_index: int
    experiment_baseline_start_index: int
    experiment_baseline_end_index: int
    experiment_plot_bessel_order: int
    experiment_plot_bessel_critical_frequency: float
    thumbnail_step: int



class ExperimentPopupPlotter:

    __slots__ = ["time", "voltage", "baseline"]

    def __init__(
        self, 
        time: np.ndarray, 
        voltage: np.ndarray, 
        baseline: np.ndarray
    ):
        """ Displays an interactive plot of a sweep's experiment epoch, along
        with a horizontal line at the baseline.

        Parameters
        ----------
        time : in seconds. Forms the domain of the plot
        voltage : in mV
        baseline: in mV

        """

        self.time = time
        self.voltage = voltage
        self.baseline = baseline

    def __call__(self) -> PlotWidget:
        
        graph = PlotWidget()
        plot = graph.getPlotItem()

        plot.setLabel("left", "membrane potential (mV)")
        plot.setLabel("bottom", "time (s)")

        plot.plot(self.time, self.voltage, pen=mkPen(color="k", width=2))
        plot.addLine(y=self.baseline, pen=mkPen(color="b", width=2), 
            label="baseline")

        return graph


class PulsePopupPlotter:

    __slots__ = ["time", "voltage", "previous", "initial", "sweep_number"]

    def __init__(
        self, 
        time: np.ndarray, 
        voltage: np.ndarray, 
        previous: Optional[np.ndarray], 
        initial: Optional[np.ndarray],
        sweep_number: int
    ):
        """ Plots the test pulse reponse, along with responses to the previous
        and first test pulse.

        Parameters
        ----------
        time : in seconds. Forms the domain of the plot
        voltage : in mV. Voltage trace from this sweep
        previous : in mV. Voltage trace from the prior sweep, or None if this is
            the first sweep.
        initial : in mV. Voltage trace from the first sweep, or None if this is
            the first sweep.
        sweep_number : identifier for this sweep

        """

        self.time = time
        self.voltage = voltage
        self.previous = previous
        self.initial = initial
        self.sweep_number = sweep_number

    def __call__(self) -> PlotWidget:

        graph = PlotWidget()
        plot = graph.getPlotItem()

        plot.setLabel("left", "membrane potential (mV)")
        plot.setLabel("bottom", "time (s)")

        plot.addLegend()
        plot.plot(self.time, self.voltage, pen=mkPen(color="k", width=2), 
            name=f"sweep {self.sweep_number}")

        if self.previous is not None:
            plot.plot(self.time, self.previous, pen=mkPen(color="b", width=2), 
                name="previous")
        
        if self.initial is not None:
            plot.plot(self.time, self.initial, pen=mkPen(color="r", width=2), 
                name="initial")

        return graph


class FixedPlots(NamedTuple):
    thumbnail: QByteArray
    full: Union[ExperimentPopupPlotter, PulsePopupPlotter]


class SweepPlotter:

    @property
    def bessel_params(self):
        if self._bessel_params is None:
            self._bessel_params = bessel(
                self.config.experiment_plot_bessel_order, 
                self.config.experiment_plot_bessel_critical_frequency, 
                "low"
            )
        return self._bessel_params


    def __init__(self, data_set: EphysDataSet, config: SweepPlotConfig):
        self.data_set = data_set
        self.config = config
        self.previous_test_voltage = None
        self.initial_test_voltage = None
        self._bessel_params = None


    def make_test_pulse_plots(self, sweep_number, sweep_data, advance=True):

        time, voltage = test_response_plot_data(
            sweep_data, 
            self.config.test_pulse_plot_start,
            self.config.test_pulse_plot_end, 
            self.config.test_pulse_baseline_samples
        )

        thumbnail = make_test_pulse_plot(sweep_number, 
            time, voltage, 
            self.previous_test_voltage, self.initial_test_voltage, 
            step=self.config.thumbnail_step, labels=False
        )

        previous = self.previous_test_voltage
        initial = self.initial_test_voltage

        if advance:
            if self.initial_test_voltage is None:
                self.initial_test_voltage = voltage
                
            self.previous_test_voltage = voltage

        return FixedPlots(
            thumbnail=svg_from_mpl_axes(thumbnail), 
            full=PulsePopupPlotter(
                time=time,
                voltage=voltage,
                previous=previous,
                initial=initial,
                sweep_number=sweep_number
            )
        )


    def make_experiment_plots(self, sweep_number, sweep_data):

        exp_time, exp_voltage, exp_baseline = experiment_plot_data(
            sweep_data, self.bessel_params[0], self.bessel_params[1], 
            self.config.backup_experiment_start_index, 
            self.config.experiment_baseline_start_index, 
            self.config.experiment_baseline_end_index
        )

        thumbnail = make_experiment_plot(sweep_number, exp_time, exp_voltage, exp_baseline, 
            step=self.config.thumbnail_step, labels=False
        )

        return FixedPlots(
            thumbnail=svg_from_mpl_axes(thumbnail),
            full=ExperimentPopupPlotter(
                time=exp_time, 
                voltage=exp_voltage, 
                baseline=exp_baseline
            )
        )


    def advance(self, sweep_number):
        sweep_data = self.data_set.sweep(sweep_number)
        return (
            self.make_test_pulse_plots(sweep_number, sweep_data), 
            self.make_experiment_plots(sweep_number, sweep_data)
        )


def svg_from_mpl_axes(fig):
    """ Convert a matplotlib figure to SVG and store it in a Qt byte array.
    """

    data = io.BytesIO()
    fig.savefig(data, format="svg")
    plt.close(fig)

    return QByteArray(data.getvalue())


def test_response_plot_data(
    sweep: Sweep, 
    test_pulse_plot_start: float = 0.0,
    test_pulse_plot_end: float = 0.1, 
    num_baseline_samples: int = 100
) -> Tuple[np.ndarray, np.ndarray]:
    """ Generate time and voltage arrays for the test pulse plots.

    Parameters
    ----------
    sweep :
        data source for one sweep
    test_pulse_plot_start :
        The start point of the plot (s)
    test_pulse_plot_end :
        The endpoint of the plot (s)
    num_baseline_samples :
        How many samples (from time 0) to use when calculating the baseline 
        mean.

    Returns
    -------
    time :
        timestamps of voltage samples (s)
    voltage :
        baseline-subtracted voltages (mV)
    """

    start_index, end_index = (
        np.searchsorted(sweep.t, [test_pulse_plot_start, test_pulse_plot_end])
        .astype(int)
    )

    return (
        sweep.t[start_index: end_index], 
        sweep.v[start_index: end_index] - np.mean(sweep.v[0: num_baseline_samples])
    )


def make_test_pulse_plot(sweep_number, time, voltage, previous=None, initial=None, step=1, labels=True):
    
    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)

    if initial is not None:
        ax.plot(time[::step], initial[::step], linewidth=1, label=f"initial", color="green")
        
    if previous is not None:
        ax.plot(time[::step], previous[::step], linewidth=1, label=f"previous", color="orange")
    
    ax.plot(time[::step], voltage[::step], linewidth=1, label=f"sweep {sweep_number}", color="blue")

    ax.set_xlabel("time (s)", fontsize=PLOT_FONTSIZE)
    ax.set_ylabel("membrane potential (mV)", fontsize=PLOT_FONTSIZE)

    if labels:
        ax.legend()
    else:
        ax.xaxis.set_major_locator(plt.NullLocator())
        ax.yaxis.set_major_locator(plt.NullLocator())

    return fig

    
def experiment_plot_data(
    sweep, 
    bessel_num, 
    bessel_denom, 
    backup_start_index: int = 5000, 
    baseline_start_index: int = 5000, 
    baseline_end_index: int = 9000
):    

    experiment_start_index, experiment_end_index = get_experiment_epoch(sweep.i, sweep.sampling_rate)# 
    
    if experiment_start_index <= 0:
        experiment_start_index = backup_start_index
    
    time = sweep.t[experiment_start_index:experiment_end_index]
    voltage = sweep.v[experiment_start_index:experiment_end_index]

    voltage[np.isnan(voltage)] = 0.0

    voltage = filtfilt(bessel_num, bessel_denom, voltage, axis=0)
    baseline_mean = np.nanmean(voltage[baseline_start_index: baseline_end_index])
    return time, voltage, baseline_mean


def make_experiment_plot(sweep_number, exp_time, exp_voltage, exp_baseline, step=1, labels=True):
    time_lim = [exp_time[0], exp_time[-1]]

    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)

    ax.plot(exp_time[::step], exp_voltage[::step], linewidth=1, label=f"sweep {sweep_number}")
    ax.hlines(exp_baseline, *time_lim, linewidth=1, label="baseline")
    ax.set_xlim(time_lim)

    ax.set_xlabel("time (s)", fontsize=PLOT_FONTSIZE)
    ax.set_ylabel("membrane potential (mV)", fontsize=PLOT_FONTSIZE)

    if labels:
        ax.legend()
    else:
        ax.xaxis.set_major_locator(plt.NullLocator())
        ax.yaxis.set_major_locator(plt.NullLocator())

    return fig



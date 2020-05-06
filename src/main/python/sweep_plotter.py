import io

from typing import NamedTuple, Tuple, Union, Optional

from PyQt5.QtCore import QByteArray

from pyqtgraph import PlotWidget, mkPen

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

from ipfx.ephys_data_set import EphysDataSet
from ipfx.sweep import Sweep
from ipfx.epochs import get_experiment_epoch


PLOT_FONTSIZE = 24
DEFAULT_FIGSIZE = (8, 8)

TEST_PULSE_CURRENT_COLOR = "#000000"
TEST_PULSE_PREV_COLOR = "#0000ff"
TEST_PULSE_INIT_COLOR = "#ff0000"

EXP_PULSE_CURRENT_COLOR = "#000000"
EXP_PULSE_BASELINE_COLOR = "#0000ff"


class SweepPlotConfig(NamedTuple):
    test_pulse_plot_start: float
    test_pulse_plot_end: float
    test_pulse_baseline_samples: int
    backup_experiment_start_index: int
    experiment_baseline_start_index: int
    experiment_baseline_end_index: int
    thumbnail_step: int


class PlotData(NamedTuple):
    """ Contains numpy arrays for each type of data: stimulus, response, time.
    This is needed due to ensure plotting doesn't break when different sampling
    rates are used in previous and initial test pulses."""
    stimulus: np.ndarray
    response: np.ndarray
    time: np.ndarray


class PopupPlotter:
    """ Stores data needed to make an interactive plot and generates it on __call__()"""
    __slots__ = ['plot_data', 'sweep_number', 'y_label']

    def __init__(self, plot_data: PlotData, sweep_number: int, y_label: str):
        """ Displays an interactive plot of a sweep

        Parameters
        ----------
        plot_data : named tuple with raw data for plotting
        sweep_number : sweep number used in naming the plot
        y_label: label for the y-axis (mV or pA)
        """
        self.plot_data = plot_data
        self.sweep_number = sweep_number
        self.y_label = y_label

    def make_graph(self):
        """ Generate an interactive plot widget from this plotter's data"""
        graph = PlotWidget()
        plot = graph.getPlotItem()

        plot.addLegend()
        plot.setLabel("left", self.y_label)
        plot.setLabel("bottom", "time (s)")

        plot.plot(self.plot_data.time, self.plot_data.response,
                  pen=mkPen(color=EXP_PULSE_CURRENT_COLOR, width=2),
                  name=f"sweep {self.sweep_number}")

        return graph

    def __call__(self):
        """ Generate an interactive plot widget from this plotter's data"""

        return self.make_graph()


class ExperimentPopupPlotter(PopupPlotter):

    __slots__ = ['plot_data', 'baseline', 'sweep_number', 'y_label']

    def __init__(
            self, plot_data: PlotData, baseline: float,
            sweep_number: int, y_label: str
    ):
        """ Displays an interactive plot of a sweep's experiment epoch, along
        with a horizontal line at the baseline.

        Parameters
        ----------
        plot_data : named tuple with raw data for plotting
        baseline: baseline mean of the initial response in mV or pA
        sweep_number : sweep number used in naming the plot
        y_label: label for the y-axis (mV or pA)

        """
        super().__init__(plot_data=plot_data, sweep_number=sweep_number, y_label=y_label)

        self.baseline = baseline

    def __call__(self) -> PlotWidget:
        """ Generate an interactive plot widget from this plotter's data """

        graph = self.make_graph()
        plot = graph.getPlotItem()

        plot.addLine(
            y=self.baseline,
            pen=mkPen(color=EXP_PULSE_BASELINE_COLOR, width=2),
            label="baseline"
        )

        return graph


class PulsePopupPlotter(PopupPlotter):

    __slots__ = ['plot_data', 'previous_plot_data', 'initial_plot_data',
                 'sweep_number', 'y_label']

    def __init__(
        self, 
        plot_data: PlotData,
        previous_plot_data: PlotData,
        initial_plot_data: PlotData,
        sweep_number: int,
        y_label: str
    ):
        """ Plots the test pulse reponse, along with responses to the previous
        and first test pulse.

        Parameters
        ----------
        plot_data : named tuple with raw data for plotting
        previous_plot_data : named tuple with previous test pulse data
        initial_plot_data : named tuple with initial test pulse data
        sweep_number : sweep number used in naming the plot
        y_label: label for the y-axis (mV or pA)

        """

        super().__init__(plot_data=plot_data, sweep_number=sweep_number, y_label=y_label)

        self.previous_plot_data = previous_plot_data
        self.initial_plot_data = initial_plot_data

    def __call__(self) -> PlotWidget:
        """ Generate an interactive plot widget from this plotter's data"""

        graph = self.make_graph()
        plot = graph.getPlotItem()

        if self.initial_plot_data is not None:
            plot.plot(self.initial_plot_data.time, self.initial_plot_data.response,
                      pen=mkPen(color=TEST_PULSE_INIT_COLOR, width=2),
                      name="initial")

        if self.previous_plot_data is not None:
            plot.plot(self.previous_plot_data.time, self.previous_plot_data.response,
                      pen=mkPen(color=TEST_PULSE_PREV_COLOR, width=2),
                      name="previous")

        return graph


class FixedPlots(NamedTuple):
    """ Each plot displayed in the sweep table comes in a thumbnail-full plot
    pair.
    """
    thumbnail: QByteArray
    full: PopupPlotter


class SweepPlotter:

    def __init__(self, data_set: EphysDataSet, config: SweepPlotConfig):
        """ Generate plots for each sweep in an experiment

        Parameters
        ----------
        data_set : plots will be generated from these experimental data
        config : parameters tweaking the generated plots

        """

        self.data_set = data_set
        self.config = config

        # initial and previous test pulse data for current clamp
        self.initial_voltage_data: Optional[PlotData] = None
        self.previous_voltage_data: Optional[PlotData] = None

        # initial and previous test pulse data for voltage clamp
        self.initial_current_data: Optional[PlotData] = None
        self.previous_current_data: Optional[PlotData] = None

    def make_test_pulse_plots(
        self, 
        sweep_number: int, 
        sweep: Sweep,
        y_label: str = "",
        advance: bool = True
    ) -> FixedPlots:
        """ Generate test pulse response plots for a single sweep

        Parameters
        ----------
        sweep_number : used to generate meaningful labels
        sweep : holds timestamps and response values for this sweep
        y_label: label for the y-axis (mV or pA)
        advance : if True, store this sweep's response for use in later plots

        """

        # defining initial and previous test response
        initial = None
        previous = None

        # grabbing data for test pulse
        plot_data = test_response_plot_data(
            sweep,
            self.config.test_pulse_plot_start,
            self.config.test_pulse_plot_end,
            self.config.test_pulse_baseline_samples
        )

        if advance:
            if sweep.clamp_mode == "CurrentClamp":
                previous = self.previous_voltage_data
                initial = self.initial_voltage_data
                if self.initial_voltage_data is None:
                    self.initial_voltage_data = plot_data
                self.previous_voltage_data = plot_data
            else:
                previous = self.previous_current_data
                initial = self.initial_current_data
                if self.initial_current_data is None:
                    self.initial_current_data = plot_data
                self.previous_current_data = plot_data

        thumbnail = make_test_pulse_plot(
            sweep_number=sweep_number, plot_data=plot_data,
            previous=previous, initial=initial, y_label=y_label,
            step=self.config.thumbnail_step, labels=False
        )

        return FixedPlots(
            thumbnail=svg_from_mpl_axes(thumbnail),
            full=PulsePopupPlotter(
                plot_data=plot_data,
                previous_plot_data=previous,
                initial_plot_data=initial,
                sweep_number=sweep_number,
                y_label=y_label
            )
        )

    def make_experiment_plots(
        self, 
        sweep_number: int, 
        sweep_data: Sweep,
        y_label: str = ""
    ) -> FixedPlots:
        """ Generate experiment response plots for a single sweep

        Parameters
        ----------
        sweep_number : used to generate meaningful labels
        sweep_data : holds timestamps and voltage values for this sweep
        y_label: label for the y-axis (mV or pA)

        """

        plot_data, exp_baseline = experiment_plot_data(
            sweep=sweep_data,
            backup_start_index=self.config.backup_experiment_start_index,
            baseline_start_index=self.config.experiment_baseline_start_index,
            baseline_end_index=self.config.experiment_baseline_end_index
        )

        thumbnail = make_experiment_plot(
            sweep_number=sweep_number, plot_data=plot_data,
            exp_baseline=exp_baseline, y_label=y_label,
            step=self.config.thumbnail_step, labels=False
        )

        return FixedPlots(
            thumbnail=svg_from_mpl_axes(thumbnail),
            full=ExperimentPopupPlotter(
                plot_data=plot_data,
                baseline=exp_baseline,
                sweep_number=sweep_number,
                y_label=y_label
            )
        )

    def advance(self, sweep_number: int):
        """ Determines what the y-label for the plots should be based on the
        clamp mode and then generates two fixed plots: one for the test pulse
        epoch and another for the experiment epoch.

        Parameters
        ----------
        sweep_number : sweep number for the sweep to be plotted

        Returns
        -------
        Tuple[FixedPlots, FixedPlots] : two thumbnail and popup plot pairs
             for the test pulse and experiment epoch of the sweep to be plotted
        """
        sweep_data = self.data_set.sweep(sweep_number)
        if sweep_data.clamp_mode == "CurrentClamp":
            y_label = "membrane potential (mV)"
        else:
            y_label = "holding current (pA)"
        return (
            self.make_test_pulse_plots(sweep_number, sweep_data, y_label),
            self.make_experiment_plots(sweep_number, sweep_data, y_label)
        )


def svg_from_mpl_axes(fig: mpl.figure.Figure) -> QByteArray:
    """ Convert a matplotlib figure to SVG and store it in a Qt byte array."""

    data = io.BytesIO()
    fig.savefig(data, format="svg")
    plt.close(fig)

    return QByteArray(data.getvalue())


def test_response_plot_data(
    sweep: Sweep, 
    test_pulse_plot_start: float = 0.0,
    test_pulse_plot_end: float = 0.1, 
    num_baseline_samples: int = 100
) -> PlotData:
    """ Generate time and response arrays for the test pulse plots.

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
    PlotData : a named tuple with the sweep's stimulus, response, and time

    """

    start_index, end_index = (
        np.searchsorted(sweep.t, [test_pulse_plot_start, test_pulse_plot_end])
        .astype(int)
    )

    return PlotData(
        stimulus=sweep.stimulus[start_index:end_index],
        response=sweep.response[start_index: end_index] - np.mean(sweep.response[0: num_baseline_samples]),
        time=sweep.t[start_index:end_index]
    )


def make_test_pulse_plot(
    sweep_number: int, 
    plot_data: PlotData,
    previous: Optional[PlotData] = None,
    initial: Optional[PlotData] = None,
    y_label: str = "",
    step: int = 1,
    labels: bool = True
) -> mpl.figure.Figure:
    """ Make a (static) plot of the response to a single sweep's test pulse, 
    optionally comparing to other sweeps from this experiment.

    Parameters
    ----------
    sweep_number : Identifier for this sweep. Used for labeling.
    plot_data : named tuple with raw data for plotting
    previous : response (mV or pA) trace for the previous sweep
    initial : response (mV or pA) trace for the first sweep in this experiment
    y_label: label for the y-axis (mV or pA)
    step : stepsize applied to each array. Can be used to generate decimated 
        thumbnails
    labels : If False, labels will not be generated (useful for thumbnails).

    Returns
    -------
    a matplotlib figure containing the plot

    """
    
    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)

    if initial is not None:
        ax.plot(initial.time[::step], initial.response[::step], linewidth=1, label=f"initial",
            color=TEST_PULSE_INIT_COLOR)

    if previous is not None:
        ax.plot(previous.time[::step], previous.response[::step], linewidth=1, label=f"previous",
            color=TEST_PULSE_PREV_COLOR)
    
    ax.plot(plot_data.time[::step], plot_data.response[::step], linewidth=1,
            label=f"sweep {sweep_number}", color=TEST_PULSE_CURRENT_COLOR)

    ax.set_xlabel("time (s)", fontsize=PLOT_FONTSIZE)

    ax.set_ylabel(y_label, fontsize=PLOT_FONTSIZE)

    if labels:
        ax.legend()
    else:
        ax.xaxis.set_major_locator(plt.NullLocator())
        ax.yaxis.set_major_locator(plt.NullLocator())

    return fig

    
def experiment_plot_data(
    sweep: Sweep,
    backup_start_index: int = 5000,
    baseline_start_index: int = 5000,
    baseline_end_index: int = 9000
) -> Tuple[PlotData, float]:
    """ Extract the data required for plotting a single sweep's experiment 
    epoch.

    Parameters
    ----------
    sweep : contains data to be extracted
    backup_start_index : if the start index of this sweep's experiment epoch
        cannot be programatically assessed, fall back to this.
    baseline_start_index : Start accumulating baseline samples from this index
    baseline_end_index : Stop accumulating baseline samples at this index

    Returns
    -------
    PlotData : a named tuple with the sweep's stimulus, response, and time

    baseline_mean : the average response (mV) during the baseline epoch for this
        sweep

    """

    # might want to grab this from sweep.epochs instead
    start_index, end_index = \
        get_experiment_epoch(sweep.i, sweep.sampling_rate) \
            or (backup_start_index, len(sweep.i))

    if start_index <= 0:
        start_index = backup_start_index
    
    stimulus = sweep.stimulus[start_index:end_index]
    response = sweep.response[start_index:end_index]
    time = sweep.t[start_index:end_index]

    response[np.isnan(response)] = 0.0
    # should mean be calculated before setting nan = 0.0?
    baseline_mean = float(np.nanmean(response[baseline_start_index: baseline_end_index]))

    return PlotData(stimulus, response, time), baseline_mean


def make_experiment_plot(
    sweep_number: int,
    plot_data: PlotData,
    exp_baseline: float,
    y_label: str,
    step: int = 1,
    labels: bool = True
) -> mpl.figure.Figure:
    """ Make a (static) plot of the response to a single sweep's stimulus

    Parameters
    ----------
    sweep_number : Identifier for this sweep. Used for labeling.
    plot_data : named tuple with raw data for plotting
    exp_baseline : the average response (mV or pA) during a period just before
        stimulation
    y_label: label for the y-axis (mV or pA)
    step : stepsize applied to each array. Can be used to generate decimated
        thumbnails
    labels : If False, labels will not be generated (useful for thumbnails).

    Returns
    -------
    a matplotlib figure containing the plot

    """

    time_lim = [plot_data.time[0], plot_data.time[-1]]

    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)

    ax.plot(plot_data.time[::step], plot_data.response[::step], linewidth=1,
            color=EXP_PULSE_CURRENT_COLOR,
            label=f"sweep {sweep_number}")
    ax.hlines(exp_baseline, *time_lim, linewidth=1, 
        color=EXP_PULSE_BASELINE_COLOR,
        label="baseline")
    ax.set_xlim(time_lim)

    ax.set_xlabel("time (s)", fontsize=PLOT_FONTSIZE)
    ax.set_ylabel(y_label, fontsize=PLOT_FONTSIZE)

    if labels:
        ax.legend()
    else:
        ax.xaxis.set_major_locator(plt.NullLocator())
        ax.yaxis.set_major_locator(plt.NullLocator())

    return fig



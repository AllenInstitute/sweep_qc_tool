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


class ExperimentPopupPlotter:

    __slots__ = ["time", "voltage", "baseline", "clamp_mode"]

    def __init__(
        self, 
        time: np.ndarray, 
        response: np.ndarray,
        baseline: np.ndarray,
        clamp_mode: str
    ):
        """ Displays an interactive plot of a sweep's experiment epoch, along
        with a horizontal line at the baseline.

        Parameters
        ----------
        time : in seconds. Forms the domain of the plot
        response : in mV
        baseline: in mV

        """

        self.time = time
        self.voltage = response
        self.baseline = baseline
        self.clamp_mode = clamp_mode

    def __call__(self) -> PlotWidget:
        """ Generate an interactive pyqtgraph plot widget from this plotter's
        data
        """

        graph = PlotWidget()
        plot = graph.getPlotItem()

        if self.clamp_mode == "CurrentClamp":
            plot.setLabel("left", "membrane potential (mV)")
        else:
            plot.setLabel("left", "holding current (pA)")
        plot.setLabel("bottom", "time (s)")

        plot.plot(self.time, self.voltage, 
            pen=mkPen(color=EXP_PULSE_CURRENT_COLOR, width=2))
        plot.addLine(y=self.baseline, 
            pen=mkPen(color=EXP_PULSE_BASELINE_COLOR, width=2), 
            label="baseline")

        return graph


class PulsePopupPlotter:

    __slots__ = ["time", "voltage", "previous", "initial", "sweep_number", "clamp_mode"]

    def __init__(
        self, 
        time: np.ndarray, 
        voltage: np.ndarray, 
        previous: Optional[np.ndarray], 
        initial: Optional[np.ndarray],
        sweep_number: int,
        clamp_mode: str
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
        self.clamp_mode = clamp_mode

    def __call__(self) -> PlotWidget:
        """ Generate an interactive pyqtgraph plot widget from this plotter's
        data
        """

        graph = PlotWidget()
        plot = graph.getPlotItem()

        plot.setLabel("bottom", "time (s)")

        plot.addLegend()

        if self.clamp_mode == "CurrentClamp":
            plot.setLabel("left", "membrane potential (mV)")

            if self.initial is not None:
                plot.plot(self.time, self.initial,
                          pen=mkPen(color=TEST_PULSE_INIT_COLOR, width=2),
                          name="initial")

            if self.previous is not None:
                plot.plot(self.time, self.previous,
                          pen=mkPen(color=TEST_PULSE_PREV_COLOR, width=2),
                          name="previous")
        else:
            plot.setLabel("left", "holding current (pA)")

        plot.plot(self.time, self.voltage, 
            pen=mkPen(color=TEST_PULSE_CURRENT_COLOR, width=2), 
            name=f"sweep {self.sweep_number}")

        return graph


PopupPlotter = Union[ExperimentPopupPlotter, PulsePopupPlotter]


class FixedPlots(NamedTuple):
    """ Each plot displayed in the sweep table comes in a thumbnail-full plot
    pair.
    """
    thumbnail: QByteArray
    full: Union[ExperimentPopupPlotter, PulsePopupPlotter]


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
        self.previous_test_voltage = None
        self.initial_test_voltage = None
        self.previous_test_current = None
        self.initial_test_current = None

    def make_test_pulse_plots(
        self, 
        sweep_number: int, 
        sweep_data: Sweep, 
        advance: bool = True
    ) -> FixedPlots:
        """ Generate test pulse response plots for a single sweep

        Parameters
        ----------
        sweep_number : used to generate meaningful labels
        sweep_data : holds timestamps and response values for this sweep
        advance : if True, store this sweep's response for use in later plots


        """
        # defining initial and previous test response
        initial = None
        previous = None

        # grabbing data for test pulse
        time, response = test_response_plot_data(
            sweep_data,
            self.config.test_pulse_plot_start,
            self.config.test_pulse_plot_end,
            self.config.test_pulse_baseline_samples
        )

        if advance:
            if sweep_data.clamp_mode == "CurrentClamp":
                previous = self.previous_test_voltage
                initial = self.initial_test_voltage
                if self.initial_test_voltage is None:
                    self.initial_test_voltage = response
                self.previous_test_voltage = response
            else:
                previous = None
                initial = None
                # TODO fix this breaking things due to different epoch lengths
                # previous = self.previous_test_current
                # initial = self.initial_test_current
                # if self.initial_test_current is None:
                #     self.initial_test_current = response
                # self.previous_test_current = response

        thumbnail = make_test_pulse_plot(
            sweep_number=sweep_number, time=time, response=response,
            clamp_mode=sweep_data.clamp_mode,
            previous=previous, initial=initial,
            step=self.config.thumbnail_step, labels=False
        )

        return FixedPlots(
            thumbnail=svg_from_mpl_axes(thumbnail), 
            full=PulsePopupPlotter(
                time=time,
                voltage=response,
                previous=previous,
                initial=initial,
                sweep_number=sweep_number,
                clamp_mode=sweep_data.clamp_mode
            )
        )

    def make_experiment_plots(
        self, 
        sweep_number: int, 
        sweep_data: Sweep
    ) -> FixedPlots:
        """ Generate experiment response plots for a single sweep

        Parameters
        ----------
        sweep_number : used to generate meaningful labels
        sweep_data : holds timestamps and voltage values for this sweep

        """

        exp_time, exp_response, exp_baseline = experiment_plot_data(
            sweep=sweep_data,
            backup_start_index=self.config.backup_experiment_start_index,
            baseline_start_index=self.config.experiment_baseline_start_index,
            baseline_end_index=self.config.experiment_baseline_end_index
        )

        thumbnail = make_experiment_plot(
            sweep_number=sweep_number, exp_time=exp_time,
            exp_response=exp_response, exp_baseline=exp_baseline,
            clamp_mode=sweep_data.clamp_mode,
            step=self.config.thumbnail_step, labels=False
        )

        return FixedPlots(
            thumbnail=svg_from_mpl_axes(thumbnail),
            full=ExperimentPopupPlotter(
                time=exp_time, 
                response=exp_response,
                baseline=exp_baseline,
                clamp_mode=sweep_data.clamp_mode
            )
        )

    def advance(self, sweep_number):
        sweep_data = self.data_set.sweep(sweep_number)
        return (
            self.make_test_pulse_plots(sweep_number, sweep_data), 
            self.make_experiment_plots(sweep_number, sweep_data)
        )


def svg_from_mpl_axes(fig: mpl.figure.Figure) -> QByteArray:
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
    time :
        timestamps of voltage samples (s)
    response :
        baseline-subtracted response (mV or pA)
    """

    start_index, end_index = (
        np.searchsorted(sweep.t, [test_pulse_plot_start, test_pulse_plot_end])
        .astype(int)
    )

    return (
        sweep.t[start_index: end_index],
        sweep.response[start_index: end_index] - np.mean(sweep.response[0: num_baseline_samples])
    )


def make_test_pulse_plot(
    sweep_number: int, 
    time: np.ndarray, 
    response: np.ndarray,
    clamp_mode: str,
    previous: Optional[np.ndarray] = None, 
    initial: Optional[np.ndarray] = None,
    step: int = 1, 
    labels: bool = True
) -> mpl.figure.Figure:
    """ Make a (static) plot of the response to a single sweep's test pulse, 
    optionally comparing to other sweeps from this experiment.

    Parameters
    ----------
    sweep_number : Identifier for this sweep. Used for labeling.
    time : timestamps (s) of voltage samples for this sweep
    response : response (mV or pA) trace for this sweep
    clamp_mode : clamp mode for this sweep ('CurrentClamp' or 'VoltageClamp')
    previous : response (mV or pA) trace for the previous sweep
    initial : response (mV or pA) trace for the first sweep in this experiment
    step : stepsize applied to each array. Can be used to generate decimated 
        thumbnails
    labels : If False, labels will not be generated (useful for thumbnails).

    Returns
    -------
    a matplotlib figure containing the plot

    """
    
    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)

    if initial is not None:
        ax.plot(time[::step], initial[::step], linewidth=1, label=f"initial",
            color=TEST_PULSE_INIT_COLOR)

    if previous is not None:
        ax.plot(time[::step], previous[::step], linewidth=1, label=f"previous",
            color=TEST_PULSE_PREV_COLOR)
    
    ax.plot(time[::step], response[::step], linewidth=1,
            label=f"sweep {sweep_number}", color=TEST_PULSE_CURRENT_COLOR)

    ax.set_xlabel("time (s)", fontsize=PLOT_FONTSIZE)
    if clamp_mode == "CurrentClamp":
        ax.set_ylabel("membrane potential (mV)", fontsize=PLOT_FONTSIZE)
    else:
        ax.set_ylabel("holding current (pA)", fontsize=PLOT_FONTSIZE)

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
) -> Tuple[np.ndarray, np.ndarray, float]:
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
    time : timestamps (s) of response samples for this sweep

    response : in (mV or pA). The response trace for this sweep's experiment epoch.

    baseline_mean : the average response (mV) during the baseline epoch for this
        sweep

    """

    # might want to grab this from sweep.epochs instead
    experiment_start_index, experiment_end_index = \
        get_experiment_epoch(sweep.i, sweep.sampling_rate) \
            or (backup_start_index, len(sweep.i))

    if experiment_start_index <= 0:
        experiment_start_index = backup_start_index
    
    time = sweep.t[experiment_start_index:experiment_end_index]
    response = sweep.response[experiment_start_index:experiment_end_index]

    response[np.isnan(response)] = 0.0

    baseline_mean = np.nanmean(response[baseline_start_index: baseline_end_index])
    return time, response, baseline_mean


def make_experiment_plot(
    sweep_number: int,
    exp_time:  np.ndarray,
    exp_response: np.ndarray,
    exp_baseline: float,
    clamp_mode: str,
    step: int = 1,
    labels: bool = True
) -> mpl.figure.Figure:
    """ Make a (static) plot of the response to a single sweep's stimulus

    Parameters
    ----------
    sweep_number : Identifier for this sweep. Used for labeling.
    exp_time : timestamps (s) of voltage samples for this sweep
    exp_response : response (mV or pA) trace for this sweep
    exp_baseline : the average response (mV or pA) during a period just before
        stimulation
    step : stepsize applied to each array. Can be used to generate decimated
        thumbnails
    labels : If False, labels will not be generated (useful for thumbnails).

    Returns
    -------
    a matplotlib figure containing the plot

    """

    time_lim = [exp_time[0], exp_time[-1]]

    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)

    ax.plot(exp_time[::step], exp_response[::step], linewidth=1,
            color=EXP_PULSE_CURRENT_COLOR,
            label=f"sweep {sweep_number}")
    ax.hlines(exp_baseline, *time_lim, linewidth=1, 
        color=EXP_PULSE_BASELINE_COLOR,
        label="baseline")
    ax.set_xlim(time_lim)

    ax.set_xlabel("time (s)", fontsize=PLOT_FONTSIZE)
    if clamp_mode == "CurrentClamp":
        ax.set_ylabel("membrane potential (mV)", fontsize=PLOT_FONTSIZE)
    else:
        ax.set_ylabel("holding current (pA)", fontsize=PLOT_FONTSIZE)

    if labels:
        ax.legend()
    else:
        ax.xaxis.set_major_locator(plt.NullLocator())
        ax.yaxis.set_major_locator(plt.NullLocator())

    return fig



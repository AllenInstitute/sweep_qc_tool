import io
from multiprocessing.connection import Connection
from typing import NamedTuple, Dict, Tuple, Optional

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
# hex color code with transparency added for previous and initial test pulses
TEST_PULSE_PREV_COLOR = "#0000ff70"
TEST_PULSE_INIT_COLOR = "#ff000070"

EXP_PULSE_CURRENT_COLOR = "#000000"
EXP_PULSE_BASELINE_COLOR = "#0000ff70"


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
    rates are used in previous and initial test pulses.
    """
    # stimulus for part of a sweep; current for I-clamp or voltage for V-clamp
    stimulus: np.ndarray
    # response for part of a sweep; voltage for I-clamp or current for V-clamp
    response: np.ndarray
    # time vector for part of a sweep
    time: np.ndarray


class PopupPlotter:
    """ Stores data needed to make an interactive plot and generates it on
    __call__()
    """

    __slots__ = ['plot_data', 'sweep_number', 'y_label', 'stimulus_code']

    def __init__(
            self, plot_data: PlotData, sweep_number: int,
            y_label: str, stimulus_code: str
    ):
        """ Displays an interactive plot of a sweep
        Parameters
        ----------
        plot_data : PlotData
            named tuple with raw data for plotting
        sweep_number : int
            sweep number used in naming the plot
        y_label: str
            label for the y-axis (mV or pA)
        stimulus_code : str
            stimulus code to use when labeling the popup window

        """
        self.plot_data = plot_data
        self.sweep_number = sweep_number
        self.y_label = y_label
        self.stimulus_code = stimulus_code

    def initialize_plot(self, graph: PlotWidget):
        """ Generates an interactive plot widget from this plotter's data. This
        function is used for easy implementation of __call__() in child classes
        Returns
        -------
        plot : PlotWidget PlotItem
            a plot item that can be plotted upon
        """
        plot = graph.getPlotItem()
        plot.addLegend()
        plot.setLabel("left", self.y_label)
        plot.setLabel("bottom", "time (s)")
        graph.setWindowTitle(f"Sweep: {self.sweep_number} - {self.stimulus_code}")

        return plot


class ExperimentPopupPlotter(PopupPlotter):
    """ Subclass of PopupPlotter used for the experiment epoch. """

    __slots__ = [
        'plot_data', 'baseline', 'sweep_number', 'y_label', 'stimulus_code'
    ]

    def __init__(
            self, plot_data: PlotData, baseline: float,
            sweep_number: int, y_label: str, stimulus_code: str
    ):
        """ Displays an interactive plot of a sweep's experiment epoch, along
        with a horizontal line at the baseline.
        Parameters
        ----------
        plot_data : PlotData
            named tuple with raw data for plotting
        baseline: float
            baseline mean of the initial response in mV or pA
        sweep_number : int
            sweep number used in naming the plot
        y_label: str
            label for the y-axis (mV or pA)
        stimulus_code : str
            stimulus code to use when labeling the popup window

        """
        super().__init__(
            plot_data=plot_data, sweep_number=sweep_number,
            y_label=y_label, stimulus_code=stimulus_code
        )

        self.baseline = baseline

    def __call__(self) -> PlotWidget:
        """ Generates an interactive plot widget from this plotter's data.
        Returns
        -------
        graph : PlotWidget
            a pyqtgraph interactive PlotWidget that pops up when user clicks
            on a thumbnail of the graph
        """
        graph = PlotWidget()
        plot = self.initialize_plot(graph)

        plot.addLine(
            y=self.baseline,
            pen=mkPen(color=EXP_PULSE_BASELINE_COLOR, width=2),
            label="baseline"
        )

        plot.plot(
            self.plot_data.time, self.plot_data.response,
            pen=mkPen(color=EXP_PULSE_CURRENT_COLOR, width=2),
            name=f"sweep {self.sweep_number}"
        )

        return graph


class PulsePopupPlotter(PopupPlotter):
    """ Subclass of PopupPlotter used for the test pulse epoch. """

    __slots__ = [
        'plot_data', 'previous_plot_data', 'initial_plot_data',
        'sweep_number', 'y_label', 'stimulus_code'
    ]

    def __init__(
            self, plot_data: PlotData,
            previous_plot_data: PlotData, initial_plot_data: PlotData,
            sweep_number: int, y_label: str, stimulus_code: str
    ):
        """ Plots the test pulse reponse, along with responses to the previous
        and first test pulse.
        Parameters
        ----------
        plot_data : : PlotData
            named tuple with raw data for plotting
        previous_plot_data : PlotData
            named tuple with previous test pulse data
        initial_plot_data : PlotData
            named tuple with initial test pulse data
        sweep_number : int
            sweep number used in naming the plot
        y_label: str
            label for the y-axis (mV or pA)
        stimulus_code : str
            stimulus code to use when labeling the popup window

        """

        super().__init__(
            plot_data=plot_data, sweep_number=sweep_number,
            y_label=y_label, stimulus_code=stimulus_code
        )

        self.previous_plot_data = previous_plot_data
        self.initial_plot_data = initial_plot_data

    def __call__(self) -> PlotWidget:
        """ Generates an interactive plot widget from this plotter's data.
        Returns
        -------
        graph : PlotWidget
            a pyqtgraph interactive PlotWidget that pops up when user clicks
            on a thumbnail of the graph
        """

        graph = PlotWidget()
        plot = self.initialize_plot(graph)

        if self.initial_plot_data is not None:
            plot.plot(
                self.initial_plot_data.time, self.initial_plot_data.response,
                pen=mkPen(color=TEST_PULSE_INIT_COLOR, width=2),
                name="initial"
            )

        if self.previous_plot_data is not None:
            plot.plot(
                self.previous_plot_data.time, self.previous_plot_data.response,
                pen=mkPen(color=TEST_PULSE_PREV_COLOR, width=2),
                name="previous"
            )

        plot.plot(
            self.plot_data.time, self.plot_data.response,
            pen=mkPen(color=TEST_PULSE_CURRENT_COLOR, width=2),
            name=f"sweep {self.sweep_number}"
        )

        return graph


class FixedPlots(NamedTuple):
    """ Each plot displayed in the sweep table comes in a thumbnail-full plot
    pair.
    """
    thumbnail: QByteArray
    full: PopupPlotter


class SweepPlotter:

    default_tp_exclude = {
        "EXTPBLWOUT", "EXTPBREAKN", "EXTPCllATT", "EXTPEXPEND", "EXTPINBATH",
        "EXTPRSCHEK", "EXTPSAFETY", "EXTPSMOKET", "EXTPGGAEND", "Search"
    }

    def __init__(self, sweep_dictionary: Dict[int, dict], config: SweepPlotConfig):
        """ Generate plots for each sweep in an experiment
        Parameters
        ----------
        sweep_dictionary : Dict[int, dict]
            A nested dictionary of Sweep objects and stimulus codes with format:
            {sweep_number: {'sweep': Sweep, 'stimulus_code': str}, ... }
            Plots will be generated from these sweeps.
        config : SweepPlotConfig
            parameters for tweaking the generated plots
        """
        self.sweep_dictionary = sweep_dictionary
        self.config = config

        # initialize only one figure and axis for efficient plotting
        self.fig, self.ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
        self.ax.set_xlabel("time (s)", fontsize=PLOT_FONTSIZE)

        # initial and previous test pulse data for current clamp
        self.initial_vclamp_data: Optional[PlotData] = None
        self.previous_vclamp_data: Optional[PlotData] = None

        # initial and previous test pulse data for voltage clamp
        self.initial_iclamp_data: Optional[PlotData] = None
        self.previous_iclamp_data: Optional[PlotData] = None

        # set of stimulus codes to not store test pulses for
        self.tp_exclude_codes = self.default_tp_exclude

    def make_test_pulse_plots(
            self,
            sweep_number: int,
            sweep: Sweep,
            y_label: str = "",
            store_test_pulse: bool = True,
            stimulus_code: str = ""

    ) -> FixedPlots:
        """ Generate test pulse response plots for a single sweep

        Parameters
        ----------
        sweep_number : int
            used to generate meaningful labels
        sweep : Sweep
            holds timestamps and response values for this sweep
        y_label: str
            label for the y-axis (mV or pA)
        store_test_pulse : bool
            if True, store this sweep's response for use in later plots
        stimulus_code : str
            stimulus code to use when labeling the popup window

        Returns
        -------
        fixed_plots : FixedPlots
            a named tuple containing a thumbnail-popup plot pair
        """

        # defining initial and previous test response
        initial = None
        previous = None

        # grabbing data for test pulse
        plot_data = self.test_response_plot_data(
            sweep,
            self.config.test_pulse_plot_start,
            self.config.test_pulse_plot_end,
            self.config.test_pulse_baseline_samples
        )

        # called for sweeps that will save initial / previous test pulses
        if store_test_pulse:
            if sweep.clamp_mode == "CurrentClamp":
                previous = self.previous_iclamp_data
                initial = self.initial_iclamp_data
                if self.initial_iclamp_data is None:
                    self.initial_iclamp_data = plot_data
                else:
                    self.previous_iclamp_data = plot_data

            else:
                previous = self.previous_vclamp_data
                initial = self.initial_vclamp_data
                if self.initial_vclamp_data is None:
                    self.initial_vclamp_data = plot_data
                else:
                    self.previous_vclamp_data = plot_data

        thumbnail = self.make_test_pulse_plot(
            sweep_number=sweep_number, plot_data=plot_data,
            previous=previous, initial=initial, y_label=y_label,
            step=self.config.thumbnail_step, labels=False
        )

        return FixedPlots(
            thumbnail=thumbnail,
            full=PulsePopupPlotter(
                plot_data=plot_data,
                previous_plot_data=previous,
                initial_plot_data=initial,
                sweep_number=sweep_number,
                y_label=y_label,
                stimulus_code=stimulus_code
            )
        )

    def make_experiment_plots(
            self,
            sweep_number: int,
            sweep_data: Sweep,
            y_label: str = "",
            stimulus_code: str = ""
    ) -> FixedPlots:
        """ Generate experiment response plots for a single sweep

        Parameters
        ----------
        sweep_number : int
            used to generate meaningful labels
        sweep_data : PlotData
            holds timestamps and voltage values for this sweep
        y_label : str
            label for the y-axis (mV or pA)
        stimulus_code : str
            stimulus code to use when labeling the popup window

        """

        plot_data, exp_baseline = self.experiment_plot_data(
            sweep=sweep_data,
            backup_start_index=self.config.backup_experiment_start_index,
            baseline_start_index=self.config.experiment_baseline_start_index,
            baseline_end_index=self.config.experiment_baseline_end_index
        )

        thumbnail = self.make_experiment_plot(
            sweep_number=sweep_number, plot_data=plot_data,
            exp_baseline=exp_baseline, y_label=y_label,
            step=self.config.thumbnail_step, labels=False
        )

        return FixedPlots(
            thumbnail=thumbnail,
            full=ExperimentPopupPlotter(
                plot_data=plot_data,
                baseline=exp_baseline,
                sweep_number=sweep_number,
                y_label=y_label,
                stimulus_code=stimulus_code
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
        # grab sweep object and stimulus code for this sweep number
        sweep_data = self.sweep_dictionary[sweep_number]['sweep']
        stim_code = self.sweep_dictionary[sweep_number]['stimulus_code']

        # skip storing the test pulse for these stimulus codes
        if any(substring in stim_code for substring in self.tp_exclude_codes):
            store_tp = False
        else:
            store_tp = True

        # determine y-axis label based on clamp mode
        if sweep_data.clamp_mode == "CurrentClamp":
            y_label = "membrane potential (mV)"
        else:
            y_label = "holding current (pA)"

        return (
            self.make_test_pulse_plots(
                sweep_number=sweep_number, sweep=sweep_data, y_label=y_label,
                store_test_pulse=store_tp, stimulus_code=stim_code
            ),
            self.make_experiment_plots(
                sweep_number=sweep_number, sweep_data=sweep_data,
                y_label=y_label, stimulus_code=stim_code)
        )

    def make_test_pulse_plot(
            self,
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
        sweep_number : int
            Identifier for this sweep. Used for labeling.
        plot_data : PlotData
            named tuple with raw data used for plotting
        previous : Optional[PlotData]
           named tuple with raw data used for the previous sweep of the same
           clamp mode
        initial : Optional[PlotData]
            named tuple with raw data used to plot the first sweep for a given
            clamp mode or stimulus code
        y_label: str
            label for the y-axis (mV or pA)
        step : int
            stepsize applied to each array. Can be used to generate decimated
            thumbnails
        labels : bool
            If False, labels will not be generated (useful for thumbnails).
        Returns
        -------
        fig : mpl.figure.Figure
            a matplotlib figure containing the plot to be turned into a thumbnail
        """

        # fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)

        if initial is not None:
            self.ax.plot(
                initial.time[::step], initial.response[::step],
                linewidth=1, label=f"initial", color=TEST_PULSE_INIT_COLOR
            )

        if previous is not None:
            self.ax.plot(
                previous.time[::step], previous.response[::step],
                linewidth=1, label=f"previous", color=TEST_PULSE_PREV_COLOR
            )

        self.ax.plot(
            plot_data.time[::step], plot_data.response[::step], linewidth=1,
                label=f"sweep {sweep_number}", color=TEST_PULSE_CURRENT_COLOR
        )

        # this is needed to avoid an error in case of an empty sweep
        if len(plot_data.time) > 0:
            time_lim = (plot_data.time[0], plot_data.time[-1])
            self.ax.set_xlim(time_lim)

        self.ax.set_xlabel("time (s)", fontsize=PLOT_FONTSIZE)
        self.ax.set_ylabel(y_label, fontsize=PLOT_FONTSIZE)

        if labels:
            self.ax.legend()
        else:
            self.ax.xaxis.set_major_locator(plt.NullLocator())
            self.ax.yaxis.set_major_locator(plt.NullLocator())

        thumbnail = self.svg_from_mpl_axes(self.fig)
        self.ax.clear()

        return thumbnail

    def make_experiment_plot(
            self,
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
        sweep_number : int
            Identifier for this sweep. Used for labeling.
        plot_data : PlotData
            named tuple with raw data for plotting
        exp_baseline : float
            the average response (mV or pA) during a period just before stimulation
        y_label: str
            label for the y-axis (mV or pA)
        step : int
            stepsize applied to each array. Can be used to generate decimated
            thumbnails
        labels : bool
            If False, labels will not be generated (useful for thumbnails).
        Returns
        -------
        fig : mpl.figure.Figure
            a matplotlib figure containing the plot to be turned into a thumbnail
        """
        if len(plot_data.time) > 0:
            time_lim = [plot_data.time[0], plot_data.time[-1]]
        else:
            time_lim = [0, 0]

        self.ax.plot(plot_data.time[::step], plot_data.response[::step], linewidth=1,
                color=EXP_PULSE_CURRENT_COLOR,
                label=f"sweep {sweep_number}")
        self.ax.hlines(exp_baseline, *time_lim, linewidth=1,
                  color=EXP_PULSE_BASELINE_COLOR,
                  label="baseline")

        self.ax.set_xlim(time_lim)

        self.ax.set_xlabel("time (s)", fontsize=PLOT_FONTSIZE)
        self.ax.set_ylabel(y_label, fontsize=PLOT_FONTSIZE)

        if labels:
            self.ax.legend()
        else:
            self.ax.xaxis.set_major_locator(plt.NullLocator())
            self.ax.yaxis.set_major_locator(plt.NullLocator())

        thumbnail = self.svg_from_mpl_axes(self.fig)
        self.ax.clear()

        return thumbnail

    @staticmethod
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
        plot_data : PlotData
            A named tuple with the sweep's stimulus, response, and time
        """

        start_index, end_index = (
            np.searchsorted(
                sweep.t, [test_pulse_plot_start, test_pulse_plot_end]
            ).astype(int)
        )

        return PlotData(
            stimulus=sweep.stimulus[start_index:end_index],
            response=sweep.response[start_index: end_index] - np.mean(sweep.response[0: num_baseline_samples]),
            time=sweep.t[start_index:end_index]
        )

    @staticmethod
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
        sweep : Sweep
            contains raw data that the experiment epoch will be extracted from
        backup_start_index : int
            Fall back on this if the experiment epoch start index cannot be
            programmatically assessed
        baseline_start_index : int
            Start accumulating baseline samples from this index
        baseline_end_index : int
            Stop accumulating baseline samples at this index
        Returns
        -------
        plot_data : PlotData
            A named tuple with the sweep's stimulus, response, and time
        baseline_mean : float
            The average response (mV) during the baseline epoch for this sweep
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

        if len(response) > baseline_end_index:
            baseline_mean = float(np.nanmean(response[baseline_start_index: baseline_end_index]))
        else:
            baseline_mean = float(np.nanmean(response))

        return PlotData(stimulus, response, time), baseline_mean

    @staticmethod
    def svg_from_mpl_axes(fig: mpl.figure.Figure) -> QByteArray:
        """ Convert a matplotlib figure to SVG and store it in a Qt byte array.
        Parameters
        ----------
        fig: mpl.figure.Figure
            a matplotlib figure containing the plot to be turned into a thumbnail
        Returns
        -------
        thumbnail : QByteArray
            a QByteArray used as a thumbnail for the given plot
        """

        data = io.BytesIO()
        fig.savefig(data, format="svg")
        plt.close(fig)

        return QByteArray(data.getvalue())


def make_plots(
        sweep_dictionary: Dict[int, dict], plot_config: SweepPlotConfig,
        plot_output: Connection
):
    """Creates a SweepPlotter object, generates fixed plot pairs, and sends
    a list of fixed plots back through the connection.

    Parameters
    ----------
    sweep_dictionary : Dict[int, dict]
        A nested dictionary of Sweep objects and stimulus codes with format:
        {sweep_number: {'sweep': Sweep, 'stimulus_code': str}, ... }
        Plots will be generated from these sweeps.
    plot_config : SweepPlotConfig
        Parameters for tweaking the plots generated by SweepPlotter
    plot_output : multiprocessing.Connection
        The output end of a multiprocessing.Pipe used to send the completed
        plots back to the parent process

    Returns
    -------
    None - Dictionary of sweep plots with format {int, [FixedPlots, FixedPlots]}
        is piped out instead through the plot_output connection

    """
    plotter = SweepPlotter(sweep_dictionary, plot_config)

    # sweep numbers must be sorted so we store test pulses correctly
    sweep_plots = {
        sweep_number: plotter.advance(sweep_number)
        for sweep_number in sorted(sweep_dictionary.keys())
    }
    plot_output.send(sweep_plots)
    plot_output.close()

import io
from typing import Dict, List, NamedTuple, Any

from PyQt5.QtWidgets import (
   QTableView, QDialog, QGridLayout
)
from PyQt5.QtCore import (
    QAbstractTableModel, QModelIndex, QByteArray, pyqtSignal
)
from PyQt5.QtGui import QColor
from PyQt5.QtSvg import QSvgWidget
from PyQt5 import QtCore

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import bessel, filtfilt

from ipfx.epochs import get_experiment_epoch
from ipfx.ephys_data_set import EphysDataSet

from delegates import (SvgDelegate, ComboBoxDelegate)
from pre_fx_data import PreFxData


PLOT_FONTSIZE = 24
DEFAULT_FIGSIZE = (8, 8)


class SweepPlotConfig(NamedTuple):
    test_plot_duration: float
    test_pulse_baseline_samples: int
    backup_experiment_start_index: int
    experiment_baseline_start_index: int
    experiment_baseline_end_index: int
    experiment_plot_bessel_order: int
    experiment_plot_bessel_critical_frequency: float
    thumbnail_step: int


class SweepTableModel(QAbstractTableModel):

    qc_state_updated = pyqtSignal(int, str, name="qc_state_updated")

    FAIL_BGCOLOR = QColor(255, 225, 225)

    def __init__(
        self, 
        colnames: List[str],
        plot_config: SweepPlotConfig
    ):
        super().__init__()
        self.colnames = colnames
        self.column_map = {colname: idx for idx, colname in enumerate(colnames)}
        self._data: List[List[Any]] = []

        self.plot_config = plot_config
    
    def connect(self, data: PreFxData):
        """ Set up signals and slots for communication with the underlying data store.

        Parameters
        ----------
        data : 
            Will be used as the underlying data store. Will emit notifications when 
            data has been updated. Will recieve notifications when users update 
            QC states for individual sweeps.

        """

        data.end_commit_calculated.connect(self.on_new_data)
        self.qc_state_updated.connect(data.on_manual_qc_state_updated)


    def on_new_data(
        self, 
        sweep_features: List[Dict], 
        sweep_states: List, 
        manual_qc_states: Dict[int, str], 
        dataset: EphysDataSet
    ):
        """ Called when the underlying data has been completely replaced

        Parameters
        ----------
        sweep_features : 
            A list of dictionaries. Each element describes a sweep.
        sweep_states : 
            A list of dictionaries. Each element contains ancillary information about
            automatic QC results for that sweep.
        manual_qc_states : 
            For each sweep, whether the user has manually passed or failed it (or left it untouched).
        dataset : 
            The underlying data. Used to extract sweepwise voltage traces

        """

        self.beginRemoveRows(QModelIndex(), 1, self.rowCount())
        self._data = []
        self.endRemoveRows()

        state_lookup = {state["sweep_number"]: state for state in sweep_states}
        plotter = SweepPlotter(dataset, self.plot_config)

        self.beginInsertRows(QModelIndex(), 1, len(sweep_features))
        for sweep in sorted(sweep_features, key=lambda swp: swp["sweep_number"]):

            sweep_number = sweep["sweep_number"]
            state = state_lookup[sweep_number]

            test_pulse_plots, experiment_plots = plotter.advance(sweep_number)

            self._data.append([
                sweep_number,
                sweep["stimulus_code"],
                sweep["stimulus_name"],
                "passed" if state["passed"] and sweep["passed"] else "failed", # auto qc
                manual_qc_states[sweep_number],
                format_fail_tags(sweep["tags"] + state["reasons"]), # fail tags
                test_pulse_plots,
                experiment_plots
            ])

        self.endInsertRows()

    def rowCount(self, *args, **kwargs):
        """ The number of sweeps
        """
        return len(self._data)

    def columnCount(self, *args, **kwargs) -> int :
        """ The number of sweep characteristics
        """
        return len(self.colnames)

    def data(self,
             index: QModelIndex,
             role: int = QtCore.Qt.DisplayRole
             ):

        """ The data stored at a given index.

        Parameters
        ----------
        index :
            Which table cell to read.
        role : 
            How the data is being accessed. Currently DisplayRole and EditRole are 
            supported.

        Returns
        -------
        None if
            - the index is invalid (e.g. out of bounds)
            - the role is not supported
        otherwise whatever data is stored at the requested index.

        """

        print(index.row(), index.column(), index.isValid(), self._data[index.row()][3], role)

        if not index.isValid():
            return

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return self._data[index.row()][index.column()]
        
        if role == QtCore.Qt.BackgroundRole and index.column() == 3:
            print("foo", QtCore.Qt.BackgroundRole)
            if self._data[index.row()][3] == "failed":
                return self.FAIL_BGCOLOR


    def headerData(
            self,
            section: int,
            orientation: int = QtCore.Qt.Horizontal,
            role: int = QtCore.Qt.DisplayRole
    ):
        """ Returns the name of the 'section'th column 
        """

        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.colnames[section]

    def flags(
            self,
            index: QModelIndex
    ) -> QtCore.Qt.ItemFlag:
        """ Returns integer flags for the item at a supplied index.
        """

        flags = super(SweepTableModel, self).flags(index)

        if index.column() == self.colnames.index("manual QC state"):
            flags |= QtCore.Qt.ItemIsEditable

        return flags

    def setData(
            self,
            index: QModelIndex,
            value: str,  # TODO: typing
            role: int = QtCore.Qt.EditRole
    ) -> bool:
        """ Updates the data at the supplied index.
        """

        current: str = self._data[index.row()][index.column()]

        if index.isValid() \
                and isinstance(value, str) \
                and index.column() == self.column_map["manual QC state"] \
                and role == QtCore.Qt.EditRole \
                and value != current:
            self._data[index.row()][index.column()] = value
            self.qc_state_updated.emit(
                self._data[index.row()][self.column_map["sweep number"]], value
            )
            return True

        return False

def format_fail_tags(tags: List[str]) -> str:
    return "\n\n".join(tags)


class SweepTableView(QTableView):

    def __init__(self, colnames):
        super().__init__()
        self.colnames = colnames
        self.svg_delegate = SvgDelegate()
        manual_qc_choices = ["default", "failed", "passed"]
        self.cb_delegate = ComboBoxDelegate(self, manual_qc_choices)

        self.setItemDelegateForColumn(self.colnames.index("test epoch"), self.svg_delegate)
        self.setItemDelegateForColumn(self.colnames.index("experiment epoch"), self.svg_delegate)
        self.setItemDelegateForColumn(self.colnames.index("manual QC state"), self.cb_delegate)

        self.verticalHeader().setMinimumSectionSize(120)

        self.clicked.connect(self.on_clicked)

        self.setWordWrap(True)


    def setModel(self, model: SweepTableModel):
        """ Attach a SweepTableModel to this view. The model will provide data for 
        this view to display.
        """
        super(SweepTableView, self).setModel(model)
        model.rowsInserted.connect(self.persist_qc_editor)
        model.rowsInserted.connect(self.resize_to_content)

    def resize_to_content(self, *args, **kwargs):
        """ This function just exists so that we can connect signals with 
        extraneous data to resizeRowsToContents
        """

        self.resizeRowsToContents()

    def resizeEvent(self, *args, **kwargs):
        """ Makes sure that we resize the rows to their contents when the user
        resizes the window
        """

        super(SweepTableView, self).resizeEvent(*args, **kwargs)
        self.resize_to_content()

    def persist_qc_editor(self, *args, **kwargs):
        """ Ensure that the QC state editor can be opened with a single click.

        Parameters
        ----------
        all are ignored. They are present because this method is triggered by a data-carrying signal.

        """

        column = self.colnames.index("manual QC state")

        for row in range(self.model().rowCount()):
            self.openPersistentEditor(self.model().index(row, column))


    def on_clicked(self, index: QModelIndex):
        """ When plot thumbnails are clicked, open a larger plot in a popup.

        Parameters
        ----------
        index : 
            Which plot to open. The popup will be mopved to this item's location.

        """
        
        if not hasattr(self.model(), "column_map"):
            return
        column_map = self.model().column_map

        if not index.column() in {column_map["test epoch"], column_map["experiment epoch"]}:
            return

        data = self.model().data(index).full
        index_rect = self.visualRect(index)        
        
        popup = QDialog()
        layout = QGridLayout()
        svg = QSvgWidget()
        svg.load(data)
        
        layout.addWidget(svg)
        popup.setLayout(layout)
        popup.move(index_rect.left(), index_rect.top())
        popup.exec()

class FixedPlots(NamedTuple):
    thumbnail: QByteArray
    full: QByteArray

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
            self.config.test_plot_duration, 
            self.config.test_pulse_baseline_samples
        )

        full = make_test_pulse_plot(sweep_number, time, voltage, 
            self.previous_test_voltage, self.initial_test_voltage
        )

        thumbnail = make_test_pulse_plot(sweep_number, 
            time, voltage, 
            self.previous_test_voltage, self.initial_test_voltage, 
            step=self.config.thumbnail_step, labels=False
        )

        if advance:
            if self.initial_test_voltage is None:
                self.initial_test_voltage = voltage
                
            self.previous_test_voltage = voltage

        return FixedPlots(thumbnail=svg_from_mpl_axes(thumbnail), full=svg_from_mpl_axes(full))

    def make_experiment_plots(self, sweep_number, sweep_data):

        exp_time, exp_voltage, exp_baseline = experiment_plot_data(
            sweep_data, self.bessel_params[0], self.bessel_params[1], 
            self.config.backup_experiment_start_index, 
            self.config.experiment_baseline_start_index, 
            self.config.experiment_baseline_end_index
        )

        full = make_experiment_plot(sweep_number, exp_time, exp_voltage, exp_baseline)
        thumbnail = make_experiment_plot(sweep_number, exp_time, exp_voltage, exp_baseline, 
            step=self.config.thumbnail_step, labels=False
        )
        return FixedPlots(thumbnail=svg_from_mpl_axes(thumbnail), full=svg_from_mpl_axes(full))

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


def test_response_plot_data(sweep, plot_duration=0.1, num_baseline_samples=100):

    timestep = sweep.t[1] - sweep.t[0]
    num_samples = int(plot_duration / timestep)

    return (
        sweep.t[0: num_samples], 
        sweep.v[0: num_samples] - np.mean(sweep.v[0: num_baseline_samples])
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

    experiment_start_index, experiment_end_index = get_experiment_epoch(sweep.i, sweep.sampling_rate)
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

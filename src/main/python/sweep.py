import io
from typing import Dict, List, NamedTuple

from PyQt5.QtWidgets import (
   QTableView, QDialog, QGridLayout
)
from PyQt5.QtCore import (
    QAbstractTableModel, QModelIndex, QByteArray, pyqtSignal
)
from PyQt5.QtSvg import QSvgWidget
from PyQt5 import QtCore

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import bessel, filtfilt

from ipfx.epochs import get_experiment_epoch
from ipfx.ephys_data_set import EphysDataSet

from delegates import (SvgDelegate, ComboBoxDelegate)
from pre_fx_data import PreFxData


class SweepPlotConfig(NamedTuple):
    test_plot_duration: float
    test_pulse_baseline_samples: int
    backup_experiment_start_index: int
    experiment_baseline_start_index: int
    experiment_baseline_end_index: int
    experiment_plot_bessel_order: int
    experiment_plot_bessel_critical_frequency: float

class SweepTableModel(QAbstractTableModel):

    qc_state_updated = pyqtSignal(int, str, name="qc_state_updated")

    def __init__(
        self, 
        colnames: List[str],
        plot_config: SweepPlotConfig
    ):
        super().__init__()
        self.colnames = colnames
        self.column_map = {colname: idx for idx, colname in enumerate(colnames)}
        self._data = []

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
        bessel_num, bessel_denom = bessel(
            self.plot_config.experiment_plot_bessel_order, 
            self.plot_config.experiment_plot_bessel_critical_frequency, 
            "low"
        )

        previous_test_voltage = None
        initial_test_voltage = None

        self.beginInsertRows(QModelIndex(), 1, len(sweep_features))
        for sweep in sorted(sweep_features, key=lambda swp: swp["sweep_number"]):
            sweep_number = sweep["sweep_number"]
            state = state_lookup[sweep_number]

            sweep_data = dataset.sweep(sweep_number)
            test_time, test_voltage = test_response_plot_data(
                sweep_data, 
                self.plot_config.test_plot_duration, 
                self.plot_config.test_pulse_baseline_samples
            )
            exp_time, exp_voltage, exp_baseline = experiment_plot_data(
                sweep_data, bessel_num, bessel_denom, 
                self.plot_config.backup_experiment_start_index, 
                self.plot_config.experiment_baseline_start_index, 
                self.plot_config.experiment_baseline_end_index
            )

            test_pulse_plot = make_test_pulse_plot(sweep_number, test_time, 
                test_voltage, previous_test_voltage, initial_test_voltage
            )
            experiment_plot = make_experiment_plot(exp_time, exp_voltage, exp_baseline)

            self._data.append([
                sweep_number,
                sweep["stimulus_code"],
                sweep["stimulus_name"],
                state["passed"] and sweep["passed"], # auto qc
                manual_qc_states[sweep_number],
                sweep["tags"] + state["reasons"], # fail tags
                svg_from_mpl_axes(test_pulse_plot),
                svg_from_mpl_axes(experiment_plot)
            ])

            if initial_test_voltage is None:
                initial_test_voltage = test_voltage
                
            previous_test_voltage = test_voltage

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

        if not index.isValid():
            return

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return self._data[index.row()][index.column()]


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

        self.clicked.connect(self.on_clicked)

    def setModel(self, model: SweepTableModel):
        """ Attach a SweepTableModel to this view. The model will provide data for 
        this view to display.
        """
        super(SweepTableView, self).setModel(model)
        model.rowsInserted.connect(self.persist_qc_editor)

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

        data = self.model().data(index)
        index_rect = self.visualRect(index)        
        
        popup = QDialog()
        layout = QGridLayout()
        svg = QSvgWidget()
        svg.load(data)
        
        layout.addWidget(svg)
        popup.setLayout(layout)
        popup.move(index_rect.left(), index_rect.top())
        popup.exec()


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


def make_test_pulse_plot(sweep_number, time, voltage, previous=None, initial=None):
    
    fig, ax = plt.subplots()

    if initial is not None:
        ax.plot(time, initial, linewidth=1, label=f"initial", color="green")
        
    if previous is not None:
        ax.plot(time, previous, linewidth=1, label=f"previous", color="orange")
    
    ax.plot(time, voltage, linewidth=1, label=f"sweep {sweep_number}", color="blue")
    return fig

    
def experiment_plot_data(
    sweep, 
    bessel_num, 
    bessel_denom, 
    backup_start_index: int = 5000, 
    baseline_start_index: int = 5000, 
    baseline_end_index: int = 9000
):    

    experiment_start_index, _ = get_experiment_epoch(sweep.i, sweep.sampling_rate)
    if experiment_start_index <= 0:
        experiment_start_index = backup_start_index
    
    time = sweep.t[experiment_start_index:]
    voltage = filtfilt(bessel_num, bessel_denom, sweep.v[experiment_start_index:], axis=0)
    baseline_mean = np.mean(voltage[baseline_start_index: baseline_end_index])
    
    return time, voltage, baseline_mean


def make_experiment_plot(exp_time, exp_voltage, exp_baseline):
    time_lim = [exp_time[0], exp_time[-1]]

    fig, ax = plt.subplots()

    ax.plot(exp_time, exp_voltage, linewidth=1)
    ax.hlines(exp_baseline, *time_lim, linewidth=1)
    ax.set_xlim(time_lim)

    return fig

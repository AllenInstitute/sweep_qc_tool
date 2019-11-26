import io

from PyQt5.QtWidgets import (
   QTableView
)
from PyQt5.QtCore import (
    QAbstractTableModel, QModelIndex, QByteArray,
)
from PyQt5 import QtCore

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import bessel, filtfilt

from ipfx.epochs import get_experiment_epoch

from delegates import (SvgDelegate, ComboBoxDelegate)
from pre_fx_data import PreFxData


class SweepTableModel(QAbstractTableModel):
    def __init__(self, colnames):
        super().__init__()
        self.colnames = colnames
        self._data = []

    
    def connect(self, data: PreFxData):
        data.end_commit_calculated.connect(self.on_new_data)


    def on_new_data(self, sweep_features, sweep_states, dataset):
        self.beginRemoveRows(QModelIndex(), 1, self.rowCount())
        self._data = []
        self.endRemoveRows()

        state_lookup = {state["sweep_number"]: state for state in sweep_states}
        bessel_num, bessel_denom = bessel(4, 0.1, "low")

        previous_test_voltage = None
        initial_test_voltage = None

        self.beginInsertRows(QModelIndex(), 1, len(sweep_features))
        for sweep in sorted(sweep_features, key=lambda swp: swp["sweep_number"]):
            sweep_number = sweep["sweep_number"]
            state = state_lookup[sweep_number]

            sweep_data = dataset.sweep(sweep_number)
            test_time, test_voltage = test_response_plot_data(sweep_data)
            exp_time, exp_voltage, exp_baseline = experiment_plot_data(
                sweep_data, bessel_num, bessel_denom
            )

            test_pulse_plot = make_test_pulse_plot(sweep_number, test_time, 
                test_voltage, previous_test_voltage, initial_test_voltage
            )
            experiment_plot = make_experiment_plot(exp_time, exp_voltage, exp_baseline)

            self._data.append([
                sweep_number,
                sweep["stimulus_code"],
                sweep["stimulus_name"],  # stimulus type
                state["passed"] and sweep["passed"], # auto qc
                "None", # manual qc
                sweep["tags"] + state["reasons"], # fail tags
                svg_from_mpl_axes(test_pulse_plot),
                svg_from_mpl_axes(experiment_plot)
            ])

        self.endInsertRows()

    def rowCount(self, parent=None, *args, **kwargs):
        """ Returns the number of rows under the given parent. When the parent
        is valid it means that rowCount is returning the number of children of
        parent.
        """
        return len(self._data)

    def columnCount(self,  parent=None, *args, **kwargs) :
        """ Returns the number of rows under the given parent. When the parent
        is valid it means that rowCount is returning the number of children of
        parent.
        """
        return len(self.colnames)

    def data(self,
             index: QModelIndex,
             role: int = QtCore.Qt.DisplayRole
             ):

        """ Returns the data stored under the given role for the item referred
        to by the index.
        """
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return self._data[index.row()][index.column()]

    def headerData(
            self,
            section: int,
            orientation: int = QtCore.Qt.Horizontal,
            role: int = QtCore.Qt.DisplayRole
    ):
        """Returns the data for the given role and section in the header with
        the specified orientation.
        """

        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.colnames[section]

    def flags(
            self,
            index: QModelIndex
    ) -> QtCore.Qt.ItemFlag:
        flags = super(SweepTableModel, self).flags(index)

        if index.column() == self.colnames.index("manual QC state"):
            flags |= QtCore.Qt.ItemIsEditable

        return flags

    def setData(
            self,
            index: QModelIndex,
            value: bool,  # TODO: typing
            role: int = QtCore.Qt.EditRole
    ) -> bool:
        if index.isValid() \
                and isinstance(value, bool) \
                and index.column() == self.colnames.index("manual QC state") \
                and role == QtCore.Qt.EditRole:
            self._data[index.row()][index.column()] = value
            return True

        return True


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

    def open_persistent_editor_on_column(self,
                                         column: int
                                         ):
        """ Make table cells editable with a single-click
        """
        for row in range(self.model().rowCount()):
            self.openPersistentEditor(self.model().index(row, column))


def tmp_mpl_svg(ct=1):

    ex = np.linspace(0, ct * np.pi, 100000)
    why = np.cos(ex)

    fig, ax = plt.subplots()

    ax.plot(ex, why)

    data = io.BytesIO()
    plt.savefig(data, format="svg")
    plt.close()


    return QByteArray(data.getvalue())


def svg_from_mpl_axes(fig):
    data = io.BytesIO()
    plt.savefig(data, format="svg")
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

    
def experiment_plot_data(sweep, bessel_num, bessel_denom):    

    experiment_start_index, _ = get_experiment_epoch(sweep.i, sweep.sampling_rate)
    if experiment_start_index <= 0:
        experiment_start_index = 5000 # aaaaaaaaaaaaaaaaaaaaaaaaaaaah
    
    time = sweep.t[experiment_start_index:]
    voltage = filtfilt(bessel_num, bessel_denom, sweep.v[experiment_start_index:], axis=0)
    baseline_mean = np.mean(voltage[5000:9000]) # aaaaaaaaaaaaaaaaaaaaaaaaaaaah
    
    return time, voltage, baseline_mean


def make_experiment_plot(exp_time, exp_voltage, exp_baseline):
    time_lim = [exp_time[0], exp_time[-1]]

    fig, ax = plt.subplots()

    ax.plot(exp_time, exp_voltage, linewidth=1)
    ax.hlines(exp_baseline, *time_lim, linewidth=1)
    ax.set_xlim(time_lim)

    return fig

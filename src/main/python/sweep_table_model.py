from typing import Optional, Dict, List, Any, Sequence

from PyQt5.QtCore import (
    QAbstractTableModel, QModelIndex, pyqtSignal   #, pyqtSlot
)
from PyQt5.QtGui import QColor
from PyQt5 import QtCore

from ipfx.ephys_data_set import EphysDataSet

from pre_fx_data import PreFxData
from sweep_plotter import SweepPlotter, SweepPlotConfig


class SweepTableModel(QAbstractTableModel):

    qc_state_updated = pyqtSignal(int, str, name="qc_state_updated")
    # clear_signal = pyqtSignal(QModelIndex, int, int, name="clear_table")
    # row_count_changed = pyqtSignal(int, int, name="row_count_changed")
    new_data = pyqtSignal(bool, name="new_data")

    FAIL_BGCOLOR = QColor(255, 225, 225)

    def __init__(
        self, 
        colnames: Sequence[str],
        plot_config: SweepPlotConfig
    ):
        super().__init__()
        self.colnames = colnames
        self.column_map = {colname: idx for idx, colname in enumerate(colnames)}
        self._data: List[List[Any]] = []

        self.plot_config = plot_config
        self.sweep_features: Optional[list] = None
    
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

        # grabbing sweep features so that sweep table view can filter based on these values
        self.sweep_features = sweep_features

        # TODO call SweepTableView.rowsAboutToBeRemoved() or .rowCountChanged() here?
        # self.clear_signal.emit(QModelIndex, 1, self.rowCount())
        # initial_row_count = self.rowCount()
        # self.row
        if self.rowCount() > 0:
            # self.rowsAboutToBeRemoved(QModelIndex, 1, self.rowCount())
            # initial_row_count = self.rowCount()
            self.beginRemoveRows(QModelIndex(), 1, self.rowCount())
            # self.clear_signal.emit(QModelIndex, 1, self.rowCount())
            self._data = []
            self.endRemoveRows()
            # self.rowsRemoved(QModelIndex, 1, initial_row_count)

        # state_lookup = {state["sweep_number"]: state for state in sweep_states}
        plotter = SweepPlotter(dataset, self.plot_config)

        self.beginInsertRows(QModelIndex(), 1, len(sweep_features))
        for index, sweep in enumerate(sweep_features):
            test_pulse_plots, experiment_plots = plotter.advance(index)

            if sweep_states[index]['passed']:
                auto_qc_state = "passed"
            elif sweep_states[index]['passed'] is None:
                auto_qc_state = "n/a"
            else:
                auto_qc_state = "failed"

            self._data.append([
                index,
                sweep["stimulus_code"],
                sweep["stimulus_name"],
                auto_qc_state,
                manual_qc_states[index],
                format_fail_tags(sweep["tags"] + sweep_states[index]['reasons']),     # fail tags
                test_pulse_plots,
                experiment_plots
            ])

        self.endInsertRows()
        # TODO fix bug where rows aren't removed in SweepTableView when a new data set is loaded
        # self.row_count_changed.emit(initial_row_count, self.rowCount())
        self.new_data.emit(True)

    def rowCount(self, *args, **kwargs):
        """ The number of sweeps
        """
        return len(self._data)

    def columnCount(self, *args, **kwargs) -> int:
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
        
        if role == QtCore.Qt.BackgroundRole and index.column() == 3:
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

        current = self._data[index.row()][index.column()]

        if index.isValid() \
                and isinstance(value, str) \
                and index.column() == self.column_map["manual QC state"] \
                and role == QtCore.Qt.EditRole \
                and value != current:
            self._data[index.row()][index.column()] = value
            # qc_state_updated may be doing the same thing as .dataChanged()
            self.qc_state_updated.emit(
                self._data[index.row()][self.column_map["sweep number"]], value
            )
            return True

        return False

    # def clear_table(self):



def format_fail_tags(tags: List[str]) -> str:
    return "\n\n".join(tags)



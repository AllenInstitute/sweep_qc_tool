from typing import Optional, Dict, List, Any, Sequence

from PyQt5.QtCore import (
    QAbstractTableModel, QModelIndex, pyqtSignal
)
from PyQt5.QtGui import QColor
from PyQt5 import QtCore

from ipfx.ephys_data_set import EphysDataSet

from pre_fx_data import PreFxData
from sweep_plotter import SweepPlotter, SweepPlotConfig


class SweepTableModel(QAbstractTableModel):
    """ Abstract table model holding the raw data for the sweep page.

    Attributes
    ----------
    qc_state_updated : pyqtSignal
        Signal that is emitted with the user updates the manual qc state.
    new_data : pyqtSignal
        Signal that is emitted when the user loads a new data set.
    FAIL_BGCOLOR : QColor
        Color that is used to pain the auto qc column when a sweep auto-fails

    """
    qc_state_updated = pyqtSignal(int, str, name="qc_state_updated")
    new_data = pyqtSignal(name="new_data")

    FAIL_BGCOLOR = QColor(255, 225, 225)

    def __init__(
        self, 
        colnames: Sequence[str],
        plot_config: SweepPlotConfig
    ):
        """ Initializes and configures abstract table model

        Parameters
        ----------
        colnames : Sequence[str]
            list of column names for the sweep table model
        plot_config : SweepPlotConfig
            named tuple with constants used for plotting sweeps

        """
        super().__init__()

        self.colnames = colnames
        self.column_map = {colname: idx for idx, colname in enumerate(colnames)}
        self._data: List[List[Any]] = []

        self.plot_config = plot_config
        self.sweep_features: Optional[list] = None
        self.sweep_states: Optional[list] = None
        self.manual_qc_states: Optional[list] = None

        self.sweep_types: Optional[Dict[str, set]] = None
    
    def connect(self, data: PreFxData):
        """ Set up signals and slots for communication with the underlying data store.

        Parameters
        ----------
        data : 
            Will be used as the underlying data store. Will emit notifications when 
            data has been updated. Will receive notifications when users update
            QC states for individual sweeps.

        """

        data.end_commit_calculated.connect(self.on_new_data)
        self.qc_state_updated.connect(data.on_manual_qc_state_updated)

    def on_new_data(
        self, 
        sweep_features: List[Dict], 
        sweep_states: List, 
        manual_qc_states: Dict[int, str], 
        data_set: EphysDataSet
    ):
        """ Called when the underlying data has been completely replaced.
        Clears any old data and populates the table model with new data.
        Emits new_data signal after the table is done being populated

        Parameters
        ----------
        sweep_features : List[dict]
            A list of dictionaries. Each element describes a sweep.
        sweep_states : List
            A list of dictionaries. Each element contains ancillary information about
            automatic QC results for that sweep.
        manual_qc_states : Dict[int, str]
            For each sweep, whether the user has manually passed or failed it
            (or left it untouched)
        data_set : EphysDataSet
            The underlying data. Used to extract sweep-wise voltage traces

        """
        # dictionary of sweep types used for filtering sweeps in table view
        self.sweep_types: Dict[str, set] = {
            'all_sweeps': set(range(len(sweep_features))),
            'v_clamp': set(), 'i_clamp': set(), 'pipeline': set(),
            'search': set(), 'ex_tp': set(), 'nuc_vc': set(),
            'core_one': set(), 'core_two': set(), 'auto_pass': set(),
            'auto_fail': set(), 'no_auto_qc': set(), 'unknown': set()
        }

        # grabbing sweep features, auto qc states, and manual qc states
        #   so that sweep table view can filter based on these values
        self.sweep_features = sweep_features
        self.sweep_states = sweep_states
        self.manual_qc_states = manual_qc_states

        # clears any data that the table is currently holding
        if self.rowCount() > 0:
            # Simply resetting the model here is easier than removing the rows
            # and then informing SweepTableView that the data has changed.
            self.beginResetModel()
            self._data = []
            self.endResetModel()

        plotter = SweepPlotter(data_set, self.plot_config)

        self.beginInsertRows(QModelIndex(), 0, len(sweep_features)-1)

        # populates the sweep table model
        for index, sweep in enumerate(sweep_features):
            # define vclamp and iclamp sweeps
            if sweep['clamp_mode'] == "VoltageClamp":
                self.sweep_types['v_clamp'].add(index)
            else:
                self.sweep_types['i_clamp'].add(index)

            # define qc pipeline sweeps
            if sweep['passed'] is not None:
                self.sweep_types['pipeline'].add(index)

            # define sweep types based on stimulus codes
            if sweep['stimulus_code'][-6:] == "Search":
                self.sweep_types['search'].add(index)
            elif sweep['stimulus_code'][0:4] == "EXTP":
                self.sweep_types['ex_tp'].add(index)
            elif sweep['stimulus_code'][0:5] == "NucVC":
                self.sweep_types['nuc_vc'].add(index)
            elif sweep['stimulus_code'][0] == "X":
                self.sweep_types['core_one'].add(index)
            elif sweep['stimulus_code'][0] == "C":
                self.sweep_types['core_two'].add(index)
            else:
                self.sweep_types['unknown'].add(index)

            # populates auto qc state column based on sweep states list
            if sweep_states[index]['passed']:
                auto_qc_state = "passed"
                self.sweep_types['auto_pass'].add(index)
            # sweep state should be None if it did not go through auto qc
            elif sweep_states[index]['passed'] is None:
                auto_qc_state = "n/a"
                self.sweep_types['no_auto_qc'].add(index)
            else:
                auto_qc_state = "failed"
                self.sweep_types['auto_fail'].add(index)

            # generate thumbnail / popup plot pairs for each sweep
            test_pulse_plots, experiment_plots = plotter.advance(index)

            # add the new row to the sweep table model
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

        # emit signal indicating that the model now has new data in it
        self.new_data.emit()

    def rowCount(self, *args, **kwargs):
        """ The number of rows in the sweep table model, which should be the
        same as the number of sweeps currently loaded in the table model

        Returns
        -------
        num_rows : int
            number of rows in the sweep table model

        """
        return len(self._data)

    def columnCount(self, *args, **kwargs) -> int:
        """ The number of columns in the sweep table model. The last two
        columns contain thumbnails for popup plots and the rest contain
        sweep characteristics and qc states.

        Returns
        -------
        num_cols : int
            number of columns in the sweep table model

        """
        return len(self.colnames)

    def data(self,
             index: QModelIndex,
             role: int = QtCore.Qt.DisplayRole
             ):

        """ The data stored at a given index.

        Parameters
        ----------
        index : QModelIndex
            Which table cell to read.
        role : QtCore.Qt.ItemDataRole
            the role for the data being accessed

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
        orientation: QtCore.Qt.Orientation = QtCore.Qt.Horizontal,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ):
        """ Returns the name of the 'section'th column

        Parameters
        ----------
        section : int
            integer index of the column to return the name for
        orientation : QtCore.Qt.Orientation
            the orientation for the data being accessed
        role : QtCore.Qt.ItemDataRole
            the display role for the data being accessed

        Returns
        -------
        colname : str
            the name of the column that is being accessed

        """

        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.colnames[section]

    def flags(
            self,
            index: QModelIndex
    ) -> QtCore.Qt.ItemFlag:
        """ Returns integer flags for the item at a supplied index.

        Parameters
        ----------
        index : QModelIndex
            index used to locate data in the model

        Returns
        -------
        flags: QtCore.Qt.ItemFlag
            describes the properties of the item being accessed

        """

        flags = super(SweepTableModel, self).flags(index)

        if index.column() == self.colnames.index("manual QC state"):
            flags |= QtCore.Qt.ItemIsEditable

        return flags

    def setData(
            self,
            index: QModelIndex,
            value: str,
            role: QtCore.Qt.ItemDataRole = QtCore.Qt.EditRole
    ) -> bool:
        """ Updates the data at the supplied index.

        Parameters
        ----------
        index : QModelIndex
            index used to locate data in the model
        value : str
            if this value is an entry in the manual QC state column and it is
            different than the current one this updates it to the new value
        role : QtCore.Qt.ItemDataRole
            the display role for the data being accessed

        Returns
        -------
        state : bool
            returns True if data was successfully updated
            returns False if data was not updated

        """

        current = self._data[index.row()][index.column()]

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
    """ Joins lists of strings containing information about the qc state
    for each sweep and joins them together in a nice readable format.

    Parameters
    ----------
    tags: List[str]
        a list of strings containing tags related to qc states

    Returns
    -------
    formatted_tags : str
        a single string containing the tags passed into this function

    """
    return "\n\n".join(tags)



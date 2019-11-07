""" Main executable for sweep qc tool
"""

import sys
import json
from pathlib import Path
from typing import Union, Optional, Dict

from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import (
    QMainWindow, QMenu, QFileDialog, QWidget, QTextEdit,
    QTabWidget, QGridLayout, QTableView
)
from PyQt5.QtCore import (
    QAbstractTableModel, QAbstractItemModel, QModelIndex, QVariant
)
from PyQt5 import QtCore
# from PyQt5.QtCore.Qt import QDisplayRole, QHorizontal

from ipfx.stimulus import StimulusOntology
from ipfx.ephys_data_set import EphysDataSet
from ipfx.data_set_utils import create_data_set
from ipfx.qc_feature_extractor import cell_qc_features, sweep_qc_features
from ipfx.qc_feature_evaluator import qc_experiment
from ipfx.bin.run_qc import qc_summary


AnyPath = Union[Path, str]


def get_default_ontology() -> StimulusOntology:
    with open(StimulusOntology.DEFAULT_STIMULUS_ONTOLOGY_FILE, "r") as default_ont_file:
        ont_data = json.load(default_ont_file)
    return StimulusOntology(ont_data)


class ExperimentData(QAbstractItemModel):
    """ Central model for a recording experiment. Has many sweeps. Corresponds
    to 1 NWB file.
    """

    def __init__(self):
        super(ExperimentData, self).__init__()
        self.init_data()


    def init_data(self):
        """ Initialize / clear this model's data
        """

        # TODO this ought to be modeled (and settable?)
        self.stimulus_ontology: StimulusOntology = get_default_ontology()
        self.qc_criteria: Optional[Dict] = None
        self.cell_qc_manual_values: Optional[Dict] = None
        self.api_sweeps: bool = True

        self.data_set: Optional[EphysDataSet] = None

        # TODO: all of these need models
        self.cell_features: Optional[Dict] = None
        self.cell_tags: Optional[Dict] = None
        self.sweep_features: Optional[Dict] = None
        self.cell_state: Optional[Dict] = None
        self.sweep_states: Optional[Dict] = None


    def load_from_nwb(self, path: AnyPath):
        """ Load data from a new NWB file, completely invalidating existing
        data held by this mode
        """

        self.beginResetModel()
        self.init_data()

        self.data_set = create_data_set(
            sweep_info=None,  # not yet!
            nwb_file=str(path),
            ontology=self.stimulus_ontology,
            api_sweeps=self.api_sweeps,
            h5_file=None,  # TODO: I think this is a mutually exclusive mode for opening pre-nwb igor-generated files
            validate_stim=True
        )

        self.cell_features, self.cell_tags = cell_qc_features(
            self.data_set,
            manual_values=self.cell_qc_manual_values
        )
        self.sweep_features = sweep_qc_features(self.data_set)
            
        self.cell_state, self.sweep_states = qc_experiment(
            ontology=self.stimulus_ontology,
            cell_features=self.cell_features,
            sweep_features=self.sweep_features,
            qc_criteria=self.qc_criteria
        )
        qc_summary(
            sweep_features=self.sweep_features, 
            sweep_states=self.sweep_states, 
            cell_features=self.cell_features, 
            cell_state=self.cell_state
        )

        print(self.cell_features)
        print(self.cell_tags)
        print(self.sweep_features)
        print(self.cell_state)
        print(self.sweep_states)

        self.endResetModel()


class SweepTable(QAbstractTableModel):


    def __init__(self):
        super(SweepTable, self).__init__()

        self.colnames = ["a", "b", "c", "d"]

        self._data = [
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [13, 14, 15, 16]
        ]


    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        """ Returns the number of rows under the given parent. When the parent 
        is valid it means that rowCount is returning the number of children of 
        parent.
        """
        return len(self._data)


    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        """ Returns the number of rows under the given parent. When the parent 
        is valid it means that rowCount is returning the number of children of 
        parent.
        """
        return len(self.colnames)


    def data(
        self,
        index: QModelIndex, 
        role: int = QtCore.Qt.DisplayRole
    ) -> QVariant:
        """ Returns the data stored under the given role for the item referred 
        to by the index.
        """
        if role == QtCore.Qt.DisplayRole:
            return QVariant(self._data[index.row()][index.column()])


    def headerData(
        self, 
        section: int, 
        orientation: int = QtCore.Qt.Horizontal, 
        role: int = QtCore.Qt.DisplayRole
    ) -> Union[int, float, str]:
        """Returns the data for the given role and section in the header with 
        the specified orientation.
        """
        if role != QtCore.Qt.DisplayRole:
            return QVariant()

        if orientation == QtCore.Qt.Horizontal:
            return QVariant(self.colnames[section])
        
        return QVariant()



class SweepView(QTableView):
    pass


class SweepPage(QWidget):
    pass


class CellPage(QWidget):
    pass


class CentralWidget(QWidget):

    def init_ui(self):

        cell_page = QTextEdit()
        sweep_page = SweepView()  # QTextEdit()

        sweep_page.setModel(SweepTable())

        layout = QGridLayout()
        self.setLayout(layout)
        layout.setSpacing(10)

        tabs = QTabWidget()
        tabs.insertTab(0, sweep_page, "sweeps")
        tabs.insertTab(1, cell_page, "cell")
        layout.addWidget(tabs)


class MainWindow(QMainWindow):
    """ The main window for this application.
    """

    def init_ui(self):
        """ Set up components for this window (and the rest of the application)
        """

        self.data: ExperimentData = ExperimentData()

        file_menu: QMenu = self.menuBar().addMenu("file")
        file_menu.addAction("load_nwb_file", self.load_nwb_dialog)

        main_widget = CentralWidget(self)
        main_widget.init_ui()

        self.setCentralWidget(main_widget)


    def load_nwb_dialog(self):
        """
        load an nwb file from the local filesystem
        """

        path: str = QFileDialog.getOpenFileName(
            self, "load NWB file", str(Path.cwd()), "NWB files (*.nwb)"
        )[0]

        if path != "":
            self.data.load_from_nwb(path)


def main():
    """ go!
    """

    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext

    window = MainWindow()
    window.resize(2000, 1600)

    window.init_ui()
    window.show()

    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)



if __name__ == '__main__':
    main()

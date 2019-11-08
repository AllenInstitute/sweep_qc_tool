""" Main executable for sweep qc tool

This is a sandbox branch. If it's been merged to master something is wrong

"""

import sys
import json
import io
from pathlib import Path
from typing import Union, Optional, Dict

from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import (
    QMainWindow, QMenu, QFileDialog, QWidget, QTextEdit,
    QTabWidget, QGridLayout, QTableView, QStyledItemDelegate, QHeaderView,
    QStyleOptionViewItem, QCheckBox, QStyleOptionButton, QApplication, QStyle
)
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtGui import QStandardItemModel, QPainter
from PyQt5.QtCore import (
    QAbstractTableModel, QAbstractItemModel, QModelIndex, QByteArray,
    QRectF
)
from PyQt5 import QtCore

import numpy as np
import matplotlib.pyplot as plt

from ipfx.stimulus import StimulusOntology
from ipfx.ephys_data_set import EphysDataSet
from ipfx.data_set_utils import create_data_set
from ipfx.qc_feature_extractor import cell_qc_features, sweep_qc_features
from ipfx.qc_feature_evaluator import qc_experiment
from ipfx.bin.run_qc import qc_summary


AnyPath = Union[Path, str]


def get_default_ontology() -> StimulusOntology:
    with open(
        StimulusOntology.DEFAULT_STIMULUS_ONTOLOGY_FILE, "r"
    ) as default_ont_file:
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
        self.stimulus_ontology: Optional[StimulusOntology] = get_default_ontology()
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
            [1, False, 3, 4],
            [5, False, 7, 8],
            [9, False, 11, 12],
            [13, False, 15, 16]
        ]

        for item in self._data:
            item[3] = tmp_mpl_svg(item[3])


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
    ):
        """ Returns the data stored under the given role for the item referred 
        to by the index.
        """
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            value = self._data[index.row()][index.column()]
            return value


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
        flags = super(SweepTable, self).flags(index) 
        
        if index.column() == 1:
            flags |= QtCore.Qt.ItemIsEditable

        return flags

    def setData(
        self,
        index: QModelIndex,
        value: bool,  # TODO: typing
        role: int = QtCore.Qt.EditRole
    ) -> bool:

        if index.column() != 1 or not isinstance(value, bool) or role != QtCore.Qt.EditRole:
            return False
        
        self._data[index.row()][1] = value
        return True



class SvgDelegate(QStyledItemDelegate):

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex
    ):

        value = index.data()

        renderer = QSvgRenderer()
        renderer.load(value)

        bounds = QRectF(
            float(option.rect.x()), 
            float(option.rect.y()), 
            float(option.rect.width()), 
            float(option.rect.height())
        )

        renderer.render(painter, bounds)
        

class CheckBoxDelegate(QStyledItemDelegate):

    def createEditor(
        self, 
        parent: QWidget, 
        option: QStyleOptionViewItem, 
        index: QModelIndex
    ) -> QCheckBox:
        editor: QCheckBox = QCheckBox(parent)
        editor.setCheckState(QtCore.Qt.Unchecked)
        return editor


    def setEditorData(
        self,
        editor: QCheckBox,
        index: QModelIndex
    ):
        value: bool = bool(index.model().data(index, QtCore.Qt.EditRole))
        if value:
            editor.setCheckState(QtCore.Qt.Checked)
        else:
            editor.setCheckState(QtCore.Qt.Unchecked)


    def setModelData(
        self,
        editor: QCheckBox,
        model: QAbstractItemModel,
        index: QModelIndex
    ):

        value = editor.checkState() == QtCore.Qt.Checked
        model.setData(index, value, QtCore.Qt.EditRole)


    def updateEditorGeometry(
        self,
        editor: QCheckBox,
        option: QStyleOptionViewItem,
        index: QModelIndex
    ):
        editor.setGeometry(option.rect)


    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex
    ):

        # During editing this is painted at the same time as the editor
        button = QStyleOptionButton()
        button.rect = option.rect
        button.state = QStyle.State_On if index.data() else QStyle.State_Off

        app = QApplication.instance()
        style = app.style()
        style.drawControl(
            QStyle.CE_CheckBox,
            button,
            painter
        )        


class SweepView(QTableView):

    def __init__(self):
        super(SweepView, self).__init__()

        self.svg_delegate = SvgDelegate()
        self.cb_delegate = CheckBoxDelegate()

        self.setItemDelegateForColumn(3, self.svg_delegate)
        self.setItemDelegateForColumn(1, self.cb_delegate)


def tmp_mpl_svg(ct=1):
    ex = np.linspace(0, ct * np.pi, 100000)
    why = np.cos(ex)

    _, ax = plt.subplots()
    
    ax.plot(ex, why)

    data = io.BytesIO()
    plt.savefig(data, format="svg")
    plt.close()
    return QByteArray(data.getvalue())


class CentralWidget(QWidget):

    def init_ui(self):

        cell_page = QSvgWidget()
        cell_page.load(tmp_mpl_svg())

        sweep_page = SweepView()

        sweep_table = SweepTable()
        # sweep_table = QStandardItemModel(4, 4)
        # colnames = ["a", "b", "c", "d"]
        # data = [
        #     [1, False, 3, tmp_mpl_svg(4)],
        #     [5, False, 7, tmp_mpl_svg(8)],
        #     [9, False, 11, tmp_mpl_svg(12)],
        #     [13, False, 15, tmp_mpl_svg(16)]
        # ]
        # for ii, row in enumerate(data):
        #     for jj, datum in enumerate(row):
        #         index = sweep_table.index(ii, jj, QModelIndex())
        #         sweep_table.setData(index, datum)

        sweep_page.setModel(sweep_table)
        sweep_page.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sweep_page.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

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

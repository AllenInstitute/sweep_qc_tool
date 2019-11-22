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

from delegates import (SvgDelegate, ComboBoxDelegate)


class SweepTableModel(QAbstractTableModel):
    def __init__(self, colnames):
        super().__init__()
        self.colnames = colnames

    def get_data(self, data=None):

        if data:
            self._data = data
        else:
            self._data = [
                [1, "abs0", "Long Square", "passed", "default", None],
                [3, "abs1", "Long Square", "passed", "default", None],
                [7, "abs2", "Short Square", "failed", "default", "Vm above threshold, Noise above threshold"],
                [13, "abs3", "Ramp", "passed", "default", None],
            ]

        for item in self._data:
            item.append(tmp_mpl_svg(item[0]))
            item.append(tmp_mpl_svg(item[0]))

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

    _, ax = plt.subplots()

    ax.plot(ex, why)

    data = io.BytesIO()
    plt.savefig(data, format="svg")
    plt.close()


    return QByteArray(data.getvalue())
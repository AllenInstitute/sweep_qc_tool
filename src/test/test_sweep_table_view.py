from unittest import mock

import pytest


from PyQt5.QtCore import QModelIndex, Qt, QPoint
from PyQt5 import QtGui

from sweep_table_view import SweepTableView
from sweep_table_model import SweepTableModel
from sweep_plotter import SweepPlotConfig
from main import SweepPage

from .conftest import check_mock_called_with, check_mock_not_called


class MockPlotter:

    def __init__(self, full):
        self._full = full

    def full(self):
        return self._full


@pytest.mark.parametrize("row", [0, 1, 2])
@pytest.mark.parametrize("col", list(range(8)))
def test_plot_popup_click(qtbot, row, col):

    model = SweepTableModel(
        SweepPage.colnames,
        SweepPlotConfig(0, 1, 2, 3, 4, 5, 6)
    )
    view = SweepTableView(
        SweepPage.colnames
    )

    view.popup_plot = mock.MagicMock()

    model.beginInsertRows(QModelIndex(), 1, row + 1)
    for ii in range(row + 1):
        model._data.append([
            ii,
            f"code_{ii}",
            f"name_{ii}",
            "passed" if ii % 2 == 0 else "failed", # auto qc
            "default",
            "", # fail tags
            MockPlotter(f"test_{ii}"),
            MockPlotter(f"exp_{ii}")
        ])

    model.endInsertRows()

    view.setModel(model)
    view.resizeRowsToContents()

    qtbot.addWidget(view)
    view.show()

    colpos = sum([view.columnWidth(pos) for pos in range(col)])
    rowpos = sum([view.rowHeight(pos) for pos in range(row)])
    point = QPoint(colpos + 1, rowpos + 1)

    qtbot.mouseClick(view.viewport(), Qt.LeftButton, Qt.NoModifier, point)

    if col in [6, 7]:
        expected = ("test" if col == 6 else "exp") + f"_{row}"
        check_mock_called_with(view.popup_plot, expected, colpos, rowpos)
    else:
        check_mock_not_called(view.popup_plot)

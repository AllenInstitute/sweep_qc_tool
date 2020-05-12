from unittest import mock

import pytest
from PyQt5.QtCore import QModelIndex, Qt, QPoint

from main import SweepPage
from sweep_plotter import SweepPlotConfig
from sweep_table_model import SweepTableModel
from sweep_table_view import SweepTableView
from .conftest import check_mock_called_with, check_mock_not_called

import pandas as pd

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
            "passed" if ii % 2 == 0 else "failed",  # auto qc
            "default",
            "",     # fail tags
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
        check_mock_called_with(view.popup_plot, expected, left=100, top=100)
    else:
        check_mock_not_called(view.popup_plot)

@pytest.mark.parametrize(
    "filter_status", [[True, True], [True, False], [False, True], [False, False]]
)
def test_filter_sweeps(qtbot, filter_status):
    model = SweepTableModel(
        SweepPage.colnames,
        SweepPlotConfig(0, 1, 2, 3, 4, 5, 6)
    )

    view = SweepTableView(
        SweepPage.colnames
    )

    features = [
        {'sweep_number': 0, 'stimulus_code': "foo", 'passed': True},
        {'sweep_number': 1, 'stimulus_code': "fooSearch", 'passed': None},
        {'sweep_number': 2, 'stimulus_code': "bar", 'passed': True},
        {'sweep_number': 3, 'stimulus_code': "foobar", 'passed': False},
        {'sweep_number': 4, 'stimulus_code': "bat", 'passed': None},
        {'sweep_number': 5, 'stimulus_code': "NucVCbat", 'passed': None},
        {'sweep_number': 6, 'stimulus_code': "NucVCbiz", 'passed': None},
        {'sweep_number': 7, 'stimulus_code': "NucVCfizz", 'passed': None}
    ]

    model.sweep_features = features
    num_rows = len(features)

    model.beginInsertRows(QModelIndex(), 1,  num_rows + 1)
    for ii in range(num_rows):
        model._data.append([
            ii,
            f"code_{ii}",
            f"name_{ii}",
            "foo",  # auto qc
            "default",
            "",     # fail tags
            MockPlotter(f"test_{ii}"),
            MockPlotter(f"exp_{ii}")
        ])
    model.endInsertRows()

    view.setModel(model)

    # setting filter checkboxes to initial values on data set loaded
    view.filter_auto_qc_sweeps_action.setChecked(True)
    view.filter_channel_sweeps_action.setChecked(False)

    # changing status to what user would select
    view.filter_auto_qc_sweeps_action.setChecked(filter_status[0])
    view.filter_channel_sweeps_action.setChecked(filter_status[1])

    if filter_status[0] and filter_status[1]:
        for index, row in enumerate(model.sweep_features):
            if row['passed'] is not None \
                    or row['stimulus_code'][0:5] == "NucVC":
                assert view.isRowHidden(index) is False
            else:
                assert view.isRowHidden(index) is True

    elif filter_status[0]:
        for index, row in enumerate(model.sweep_features):
            if row['passed'] is not None:
                assert view.isRowHidden(index) is False
            else:
                assert view.isRowHidden(index) is True

    elif filter_status[1]:
        for index, row in enumerate(model.sweep_features):
            if row['stimulus_code'][0:5] == "NucVC":
                assert view.isRowHidden(index) is False
            else:
                assert view.isRowHidden(index) is True

    else:
        for index, row in enumerate(model.sweep_features):
            if row['stimulus_code'][-6:] != "Search":
                assert view.isRowHidden(index) is False
            else:
                assert view.isRowHidden(index) is True

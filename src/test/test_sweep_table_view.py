from unittest import mock

import pytest
from PyQt5.QtCore import QModelIndex, Qt, QPoint

from main import SweepPage
from sweep_plotter import SweepPlotConfig
from sweep_table_model import SweepTableModel
from sweep_table_view import SweepTableView
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

    # mock dictionary of sets defining sweep types
    sweep_types = {
        'v_clamp': {
            0, 1, 2, 3, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71
        },
        'i_clamp': {
            4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
            22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38,
            39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55,
            56, 57, 58, 59, 72
        },
        'pipeline': {
            4, 6, 7, 8, 10, 11, 13, 15, 24, 25, 26, 27, 29, 32, 33, 34, 45, 46,
            47, 48, 49, 50, 51, 57, 58, 59
        },
        'search': {
            35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 16, 17, 18, 19, 20, 21, 22
        },
        'ex_tp': {0, 1, 2, 3, 60},
        'nuc_vc': {61, 62, 63, 64, 65, 66, 67, 68, 69, 70},
        'core_one': {
            4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 23, 24, 25, 26, 27, 28,
            29, 30, 31, 32, 33, 34, 45, 46, 47, 48, 49, 50, 51
        },
        'core_two': {52, 53, 54, 55, 56, 57, 58, 59},
        'unknown': {71, 72},
        'auto_pass': {
            4, 6, 7, 8, 11, 13, 15, 24, 25, 26, 27, 32, 33, 34, 45, 46, 47, 48,
            49, 50, 51, 57, 58, 59
        },
        'auto_fail': {
            5, 9, 10, 12, 14, 52, 53, 54, 23, 55, 56, 28, 29, 30, 31
        },
        'no_auto_qc': {
            0, 1, 2, 3, 16, 17, 18, 19, 20, 21, 22, 35, 36, 37, 38, 39, 40, 41,
            42, 43, 44, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71
        }
    }

    model.sweep_types = sweep_types

    # creating a set of all sweeps to determine number of rows
    all_sweeps = set()
    for value in sweep_types.values():
        all_sweeps.update(value)
    num_rows = len(all_sweeps)

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
        for index in range(num_rows):
            if index in sweep_types['pipeline'].union(sweep_types['nuc_vc']
            ):
                assert view.isRowHidden(index) is False
            else:
                assert view.isRowHidden(index) is True

    elif filter_status[0]:
        for index in range(num_rows):
            if index in sweep_types['pipeline']:
                assert view.isRowHidden(index) is False
            else:
                assert view.isRowHidden(index) is True

    elif filter_status[1]:
        for index in range(num_rows):
            if index in sweep_types['nuc_vc']:
                assert view.isRowHidden(index) is False
            else:
                assert view.isRowHidden(index) is True

    else:
        for index in range(num_rows):
            if index not in sweep_types['search']:
                assert view.isRowHidden(index) is False
            else:
                assert view.isRowHidden(index) is True

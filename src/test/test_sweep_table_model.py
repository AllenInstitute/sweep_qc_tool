import pytest

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtGui import QColor

from sweep import SweepTableModel, SweepPlotConfig

@pytest.fixture
def model():
    return SweepTableModel(
        ["a", "b", "c"],
        SweepPlotConfig(1, 2, 3, 4, 5, 6, 7, 8)
    )


class MockIndex:
    def __init__(self, valid, row, column):
        self.valid = valid
        self._row = row
        self._column = column

    def isValid(self):
        return self.valid

    def row(self):
        return self._row

    def column(self):
        return self._column


@pytest.mark.parametrize("index,role,expected", [
    [MockIndex(True, 0, 3), Qt.BackgroundRole, SweepTableModel.FAIL_BGCOLOR],
    [MockIndex(True, 1, 3), Qt.BackgroundRole, None],
    [MockIndex(True, 0, 4), Qt.BackgroundRole, None],
    [MockIndex(True, 0, 3), Qt.DisplayRole, "failed"],
    [MockIndex(False, 0, 3), Qt.DisplayRole, None]
])
def test_data(index, role, expected, model):

    model._data.append(["a", "b", "c", "failed", "d", "e", "f", "g"])
    model._data.append(["a", "b", "c", "passed", "d", "e", "f", "g"])

    obtained = model.data(index, role)
    if obtained is None:
        assert expected is None
    else:
        assert obtained == expected
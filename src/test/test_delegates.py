import pytest
import pytest_check as check

from PyQt5.QtWidgets import QComboBox, QApplication, QMainWindow
from PyQt5.QtCore import Qt

import numpy as np

from delegates import ComboBoxDelegate

from .conftest import check_allclose


def test_combobox_activated(qtbot):

    record = []
    def set_record(_, b):
        record.append(b)

    delegate = ComboBoxDelegate(None, ["a", "b", "c"])
    delegate.setModelData = set_record

    dummy = QMainWindow()
    cb = delegate.createEditor(dummy, None, None)
    qtbot.addWidget(cb)

    app = QApplication.instance()
    app.setActiveWindow(dummy)
    cb.setFocus()

    cb.activated.emit(12)

    check.is_none(app.focusWidget())
    check_allclose(record, [12])
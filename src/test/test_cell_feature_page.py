import pytest
import pytest_check as check

from PyQt5.QtWidgets import QWidget

import numpy as np

from cell_feature_page import CellFeaturePage, format_feature, get_feature


@pytest.fixture
def page():
    def get_keys():
        return {
            "a": ["fish", "fowl"],
            "b": ["bike", "car"]
        }
    return CellFeaturePage(get_keys=get_keys)


def test_clear(qtbot, page):
    widget = QWidget()
    qtbot.addWidget(widget)

    page.central_layout.addWidget(widget)
    page.clear()
    
    check.is_none(widget.parent())
    check.equal(page.central_layout.count(), 0)


def test_on_new_data(page):
    data = {
        "cell_record": {
            "fish": 12,
            "fowl": "hello",
            "bike": None,
            "car": np.float64(12)
        }
    }
    page.on_new_data(data)

    check.equal(page.central_layout.count(), 3)
    # need to indirect through intermediate category widget, cell feature, to 
    # finally get to the value Qlabel
    check.equal(
        page.central_layout
        .itemAt(2).widget()
        .layout().itemAt(0).widget()
        .layout().itemAt(2).widget()
        .text(),
        "None"
    )


@pytest.mark.parametrize("inpt,expct", [
    [0.123456, "0.1235"],
    [np.array([12])[0], "12"],
    [None, "None"],
    ["foo", "foo"]
])
def test_format_feature(inpt, expct):
    obtained = format_feature(inpt)
    assert obtained == expct


@pytest.mark.parametrize("data,path,expct", [
    [{"a": {"b": 2}}, ["a", "b"], "2"]
])
def test_get_feature(data, path, expct):
    obtained = get_feature(data, *path)
    assert obtained == expct


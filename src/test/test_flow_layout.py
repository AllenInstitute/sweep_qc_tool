import pytest

from PyQt5.QtCore import QSize

from flow_layout import FlowLayout


@pytest.fixture
def layout():
    return FlowLayout(margin=12, horizontal_spacing=24, vertical_spacing=36)

def test_hspacing_accessor(layout):
    assert layout.horizontalSpacing() == 24

def test_vspacing_accessor(layout):
    assert layout.verticalSpacing() == 36

def test_add_item(layout):
    assert layout.count() == 0
    layout.addItem("foo")
    assert layout.count() == 1

def test_item_at(layout):
    layout.addItem("foo")
    assert layout.itemAt(0) == "foo"

def test_take_at(layout):
    layout.addItem("foo")
    assert layout.takeAt(0) == "foo"
    assert layout.count() == 0

def test_minimum_size(layout):
    class SquareItem:
        def __init__(self, minsize: int):
            self.minsize = QSize(minsize, minsize)
        def minimumSize(self):
            return self.minsize

    layout.addItem(SquareItem(4))
    layout.addItem(SquareItem(8))
    assert QSize(32, 32) == layout.minimumSize()

def test_do_layout(layout):
    raise NotImplementedError()
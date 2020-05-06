import pytest
import pytest_check as check

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QSize, QRect

from flow_layout import FlowLayout


class RectangularItem:
    def __init__(self, minsize: int):
        self.minsize = QSize(minsize + 2, minsize)

    def minimumSize(self):
        return self.minsize


class SquareWidget(QWidget):
    def __init__(self, size: int):
        super(SquareWidget, self).__init__()
        self.size = QSize(size, size)

    def sizeHint(self):
        return self.size

    def widget(self):
        return "foo"


@pytest.fixture
def layout():
    return FlowLayout(margin=12, horizontal_spacing=24, vertical_spacing=36)

def test_hspacing_accessor(layout):
    assert layout.horizontalSpacing() == 24

def test_vspacing_accessor(layout):
    assert layout.verticalSpacing() == 36

def test_add_item(layout):
    check.equal(layout.count(), 0)
    layout.addItem("foo")
    check.equal(layout.count(), 1)
    
def test_item_at(layout):
    layout.addItem("foo")
    assert layout.itemAt(0) == "foo"

def test_take_at(layout):
    layout.addItem("foo")
    check.equal(layout.takeAt(0), "foo")
    check.equal(layout.count(), 0)

def test_minimum_size(layout):
    layout.addItem(RectangularItem(4))
    layout.addItem(RectangularItem(8))
    assert QSize(34, 32) == layout.minimumSize()


# TODO this test fails in master branch
def test_do_layout(layout):
    first = SquareWidget(20)
    second = SquareWidget(30)

    layout.addItem(first)
    layout.addItem(second)

    layout.doLayout(QRect(0, 0, 50, 1000), False)

    check.equal(first.geometry(), QRect(12, 12, 20, 20))
    check.equal(second.geometry(), QRect(12, 68, 30, 30)) # next row

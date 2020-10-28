from PyQt5.QtWidgets import (
    QStyledItemDelegate, QItemDelegate,
    QStyleOptionViewItem, QApplication, QStyle, QStyleOptionComboBox,
    QComboBox
)
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import QModelIndex, QRectF
from PyQt5 import QtCore


class SvgDelegate(QStyledItemDelegate):

    def paint(
            self,
            painter: QPainter,
            option: QStyleOptionViewItem,
            index: QModelIndex
    ):
        value = index.data().thumbnail

        renderer = QSvgRenderer()
        renderer.load(value)

        bounds = QRectF(
            float(option.rect.x()),
            float(option.rect.y()),
            float(option.rect.width()),
            float(option.rect.height())
        )

        renderer.render(painter, bounds)


class ComboBoxDelegate(QItemDelegate):
    def __init__(self, owner, choices):
        super().__init__(owner)
        self.items = choices

    def createEditor(self, parent, option, index):

        editor = QComboBox(parent)
        editor.addItems(self.items)
        editor.activated.connect(self.onActivated)

        return editor

    def paint(self, painter, option, index):
        value = index.data(QtCore.Qt.DisplayRole)
        style = QApplication.style()
        opt = QStyleOptionComboBox()
        opt.text = str(value)
        opt.rect = option.rect
        style.drawComplexControl(QStyle.CC_ComboBox, opt, painter)
        QItemDelegate.paint(self, painter, option, index)

    def onActivated(self):
        """ Triggered when the user makes a selection. When that occurs, focus 
        is removed from the editing combobox, which in turn causes 
        setModelData to be called on this delegate.
        """

        app = QApplication.instance()

        sender = app.sender()
        focus = app.focusWidget()

        if sender is focus:
            focus.clearFocus()

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.DisplayRole)
        num = self.items.index(value)
        editor.setCurrentIndex(num)

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

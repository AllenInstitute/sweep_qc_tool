from PyQt5.QtWidgets import (
    QWidget,
    QStyledItemDelegate, QItemDelegate,
    QStyleOptionViewItem, QApplication, QStyle, QStyleOptionComboBox,
    QComboBox
)
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtGui import QStandardItemModel, QPainter
from PyQt5.QtCore import (
    QModelIndex, QByteArray,
    QRectF, QPoint
)
from PyQt5 import QtCore


class SvgDelegate(QStyledItemDelegate):

    def paint(
            self,
            painter: QPainter,
            option: QStyleOptionViewItem,
            index: QModelIndex
    ):
        value = index.data()

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
        self.editor = QComboBox(parent)
        self.editor.addItems(self.items)
        return self.editor

    def paint(self, painter, option, index):
        value = index.data(QtCore.Qt.DisplayRole)
        style = QApplication.style()
        opt = QStyleOptionComboBox()
        opt.text = str(value)
        opt.rect = option.rect
        style.drawComplexControl(QStyle.CC_ComboBox, opt, painter)
        QItemDelegate.paint(self, painter, option, index)

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.DisplayRole)
        num = self.items.index(value)
        editor.setCurrentIndex(num)

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

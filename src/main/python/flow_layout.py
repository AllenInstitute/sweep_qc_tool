""" A Python version of the flow layout example from the QT5 docs. See here:
https://doc.qt.io/qt-5/qtwidgets-layouts-flowlayout-example.html
for the C++ example.
"""

from typing import List

from PyQt5.QtWidgets import QLayout, QLayoutItem, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QSize, QMargins, QPoint


class FlowLayout(QLayout):


    def __init__(
        self, 
        margin: int = 11, 
        horizontal_spacing: int = 11, 
        vertical_spacing: int = 11
    ):
        """ Items are ordered 1-dimensionally, from left to right. When the 
        available horizontal space is exceeded, items are placed on a new row.

        Parameters
        ----------
        margin: 
            symmetric margin around layout space (px)
        horizontal_spacing : 
            between items (px)
        vertical_spacing :
            between items (px)

        """

        super(FlowLayout, self).__init__()

        self.items: List[QLayoutItem] = []

        self.vertical_spacing = vertical_spacing
        self.horizontal_spacing = horizontal_spacing

        self.setContentsMargins(margin, margin, margin, margin)


    def horizontalSpacing(self):
        return self.horizontal_spacing

    def verticalSpacing(self):
        return self.vertical_spacing

    def addItem(self, item):
        self.items.append(item)
    
    def count(self) -> int:
        return len(self.items)

    def itemAt(self, index: int):
        if index >= len(self.items):
            return
        return self.items[index]

    def takeAt(self, index: int):
        return self.items.pop(index)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width: int):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def expandingDirections(self):
        return Qt.Horizontal | Qt.Vertical

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size: QSize = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())

        margins: QMargins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect: QRect, testOnly: bool):
        left, top, right, bottom = self.getContentsMargins()
        actual_rect: QRect = rect.adjusted(left, top, -right, -bottom)
        
        horizontal: int = actual_rect.x()
        vertical: int = actual_rect.y()
        line_height: int = 0

        for item in self.items:
            widget = item.widget()
            horizontal_space = self.horizontalSpacing()
            vertical_space = self.verticalSpacing()

            if horizontal_space == -1:
                horizontal_space = widget.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
                )
            if vertical_space == -1:
                vertical_space = widget.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
                )

            next_horizontal: int = horizontal + item.sizeHint().width() + horizontal_space
            if next_horizontal - horizontal_space > actual_rect.right() and line_height > 0:
                horizontal = actual_rect.x()
                vertical = vertical + line_height + vertical_space
                next_horizontal = horizontal + item.sizeHint().width() + horizontal_space
                line_height = 0
            
            if not testOnly:
                item.setGeometry(QRect(QPoint(horizontal, vertical), item.sizeHint()))
            
            horizontal = next_horizontal
            line_height = max(line_height, item.sizeHint().height())

        return vertical + line_height - rect.y() + bottom

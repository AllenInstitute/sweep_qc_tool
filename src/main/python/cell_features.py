from typing import List

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLayout, QLayoutItem, QSizePolicy, QStyle, QFrame
from PyQt5.QtCore import Qt, QRect, QSize, QMargins, QPoint


class CellFeature(QFrame):

    def __init__(self, key, value, *args, **kwargs):
        super(CellFeature, self).__init__(*args, **kwargs)
        self.setFrameStyle(QFrame.WinPanel | QFrame.Raised)

        key_label = QLabel()
        key_label.setText(f"<b>{key}</b>")
        key_label.setAlignment(Qt.AlignCenter)

        divider = QFrame()
        divider.setFrameStyle(QFrame.HLine)

        value_label = QLabel()
        value_label.setText(value)
        value_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(key_label)
        layout.addWidget(divider)
        layout.addWidget(value_label)
        self.setLayout(layout)


class FlowLayout(QLayout):


    def __init__(
        self, 
        margin: int, 
        horizontal_spacing: int, 
        vertical_spacing: int
    ):
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

    def expandingDirections(self):
        return 0

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width: int):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

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
        effectiveRect: QRect = rect.adjusted(left, top, -right, -bottom)
        
        x: int = effectiveRect.x()
        y: int = effectiveRect.y()
        lineHeight: int = 0

        for item in self.items:
            widget = item.widget()
            spaceX = self.horizontalSpacing()
            spaceY = self.verticalSpacing()

            if spaceX == -1:
                spaceX = widget.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            if spaceY == -1:
                spaceY = widget.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)

            nextX: int = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + bottom

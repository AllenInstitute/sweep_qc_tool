""" A box for displaying a key-value pair separated by a horizontal bar
"""

from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt


class CellFeatureView(QFrame):

    def __init__(self, key, value, *args, **kwargs):
        super(CellFeatureView, self).__init__(*args, **kwargs)
        self.setFrameStyle(QFrame.WinPanel | QFrame.Raised)

        key_label = QLabel()
        key_label.setText(f"{key}")
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

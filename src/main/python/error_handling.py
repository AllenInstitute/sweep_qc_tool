import sys
from traceback import format_tb

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QGridLayout, QTextEdit, QPushButton, QLabel


def exception_message(title: str, summary: str, exception: Exception):
    traceback = r"<br \><br \>".join(format_tb(sys.exc_info()[-1]))
    message = str(exception)

    details = f"<p><b>{message}</b></p><p>{traceback}</p>"
    error_message(title, summary, details)

            
def error_message(title: str, summary: str, details: str):
    dialog = QDialog()
    layout = QGridLayout()

    dialog.setWindowTitle(title)

    summary_label = QLabel()
    summary_label.setText(summary)
    summary_label.setAlignment(Qt.AlignCenter)

    details_view = QTextEdit()
    details_view.setReadOnly(True)
    details_view.setText(details)

    close_button = QPushButton("ok")
    close_button.clicked.connect(dialog.close)

    layout.addWidget(summary_label, 1, 1, 1, 5)
    layout.addWidget(details_view, 2, 1, 1, 5)
    layout.addWidget(close_button, 3, 3, 1, 1)

    dialog.setLayout(layout)
    dialog.exec()
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QMenu, QWidget, QTabWidget,
    QTableView, QGraphicsView,
    QMenuBar,
    QVBoxLayout, QHBoxLayout
)
from PyQt5.QtCore import pyqtSignal
from pyqtgraph import GraphicsLayoutWidget

from fbs_runtime.application_context.PyQt5 import ApplicationContext

from settings import Settings
from pre_fx_data import PreFxData


class SweepPage(QTableView):
    def __init__(self):
        super().__init__()


class CellPage(QWidget):
    def __init__(self):
        super().__init__()

        cell_features_table = QTableView()
        cell_plots = CellPlotsView()

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(cell_features_table,1)
        layout.addWidget(cell_plots,3)


class CellPlotsView(QGraphicsView):
    def __init__(self):
        super().__init__()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Configure window
        self.setWindowTitle("Ephys Sweep QC Tool")
        self.resize(800, 1000)

        # Create tab pages
        sweep_page = SweepPage()
        cell_page = CellPage()

        # Create tab widget
        tab_widget = QTabWidget()
        tab_widget.insertTab(0, sweep_page, "Sweeps")
        tab_widget.insertTab(1, cell_page, "Cell")

        # Set tabs as a central widget
        self.setCentralWidget(tab_widget)


    def create_main_menu_bar(self, settings_data: Settings):

        self.main_menu_bar = self.menuBar()
        self.file_menu = self.main_menu_bar.addMenu("File")
        self.main_menu_bar.addMenu("Edit")
        self.main_menu_bar.addMenu("Settings")
        self.main_menu_bar.addMenu("Help")

        self.file_menu.addAction("Load NWB file", settings_data.load_nwb_file)
        self.file_menu.addAction("Load from LIMS")
        self.file_menu.addSeparator()
        self.file_menu.addAction("Export to JSON")
        self.file_menu.addAction("Export to LIMS")





class Application(object):

    def __init__(self):
        self.app_cntxt = ApplicationContext()

        self.settings: Settings = Settings()
        self.pre_fx_data: PreFxData = PreFxData()
        self.main_window = MainWindow()

        self.settings.connect(self.pre_fx_data)
        self.pre_fx_data.connect(self.settings)

        self.main_window.create_main_menu_bar(self.settings)
        self.settings.load_stimulus_ontology()



    def run(self):
        self.main_window.show()
        return self.app_cntxt.app.exec_()


if __name__ == '__main__':
    app = Application()
    exit_code = app.run()
    sys.exit(exit_code)




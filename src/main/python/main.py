import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QMenu, QWidget, QTabWidget,
    QTableView, QGraphicsView,
    QHeaderView,
    QVBoxLayout, QHBoxLayout,
    QFileDialog
)
from PyQt5.QtCore import pyqtSignal
from pyqtgraph import GraphicsLayoutWidget

from fbs_runtime.application_context.PyQt5 import ApplicationContext

from sweep import SweepTableView, SweepTableModel
from pre_fx_data import PreFxData
from pre_fx_controller import PreFxController

class SweepPage(QWidget):
    def __init__(self):
        super().__init__()

        self.colnames = ["sweep number",
                         "sweep name",
                         "stimulus type",
                         "auto QC state",
                         "manual QC state",
                         "fail tags",
                         "test epoch",
                         "experiment epoch"
                         ]

        sweep_view = SweepTableView(self.colnames)

        sweep_model = SweepTableModel(self.colnames)
        sweep_model.get_data()

        sweep_view.setModel(sweep_model)
        sweep_view.open_persistent_editor_on_column(4)

        layout = QVBoxLayout()
        layout.addWidget(sweep_view)
        self.setLayout(layout)

        sweep_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sweep_view.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)


class FeaturePage(QWidget):
    def __init__(self):
        super().__init__()

        cell_features_table = QTableView()

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(cell_features_table)

class PlotPage(QWidget):
    def __init__(self):
        super().__init__()

        cell_plots = CellPlotsView()

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(cell_plots)


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
        feature_page = FeaturePage()
        plot_page = PlotPage()

        # Create tab widget
        tab_widget = QTabWidget()
        tab_widget.insertTab(0, sweep_page, "Sweeps")
        tab_widget.insertTab(1, feature_page, "Features")
        tab_widget.insertTab(2, plot_page, "Plots")

        # Set tabs as a central widget
        self.setCentralWidget(tab_widget)


    def create_main_menu_bar(self, pre_fx_controller: PreFxController):

        self.main_menu_bar = self.menuBar()
        self.file_menu = self.main_menu_bar.addMenu("File")
        self.main_menu_bar.addMenu("Edit")
        self.settings_menu = self.main_menu_bar.addMenu("Settings")
        self.main_menu_bar.addMenu("Help")

        self.file_menu.addAction(
            pre_fx_controller.load_data_set_action
        )
        self.file_menu.addAction("Load from LIMS")
        self.file_menu.addSeparator()
        self.file_menu.addAction(pre_fx_controller.export_manual_states_to_json_action)
        self.file_menu.addAction("Export manual states to LIMS")
        self.file_menu.addSeparator()
        self.file_menu.addAction(
            pre_fx_controller.load_stimulus_ontology_action
        )
        self.file_menu.addSeparator()
        self.file_menu.addAction(
            pre_fx_controller.load_qc_criteria_action
        )

        self.settings_menu.addAction(pre_fx_controller.show_stimulus_ontology_action)
        self.settings_menu.addAction(pre_fx_controller.show_qc_criteria_action)


class Application(object):

    def __init__(self):
        self.app_cntxt = ApplicationContext()

        self.pre_fx_controller: PreFxController = PreFxController()
        self.pre_fx_data: PreFxData = PreFxData()

        self.main_window = MainWindow()

        self.pre_fx_controller.connect(self.pre_fx_data)
        self.main_window.create_main_menu_bar(self.pre_fx_controller)

        self.pre_fx_data.set_default_stimulus_ontology()
        self.pre_fx_data.set_default_qc_criteria()

    def run(self):
        self.main_window.show()
        return self.app_cntxt.app.exec_()


if __name__ == '__main__':
    import logging; logging.getLogger().setLevel(logging.INFO)
    app = Application()
    exit_code = app.run()
    sys.exit(exit_code)




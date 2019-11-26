import sys
from pathlib import Path
import argparse

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

    colnames: tuple = (
        "sweep number",
        "stimulus code",
        "stimulus type",
        "auto QC state",
        "manual QC state",
        "fail tags",
        "test epoch",
        "experiment epoch"
    )

    def __init__(self):
        super().__init__()

        self.sweep_view = SweepTableView(self.colnames)
        self.sweep_model = SweepTableModel(self.colnames)

        self.sweep_view.setModel(self.sweep_model)

        layout = QVBoxLayout()
        layout.addWidget(self.sweep_view)
        self.setLayout(layout)

        self.sweep_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sweep_view.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def connect_model(self, data: PreFxData):
        self.sweep_model.connect(data)


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

        # Create tab widget & set tabs as a central widget
        tab_widget = QTabWidget()
        self.setCentralWidget(tab_widget)


    def insert_tabs(self, sweep_page, feature_page, plot_page):
        self.centralWidget().insertTab(0, sweep_page, "Sweeps")
        self.centralWidget().insertTab(1, feature_page, "Features")
        self.centralWidget().insertTab(2, plot_page, "Plots")


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

    def __init__(self, output_dir):
        self.app_cntxt = ApplicationContext()

        # initialize components
        self.main_window = MainWindow()
        self.pre_fx_controller: PreFxController = PreFxController()
        self.pre_fx_data: PreFxData = PreFxData()
        self.sweep_page = SweepPage()
        self.feature_page = FeaturePage()
        self.plot_page = PlotPage()

        # set cmdline params
        self.pre_fx_controller.set_output_path(output_dir)

        # connect components
        self.pre_fx_controller.connect(self.pre_fx_data)
        self.sweep_page.connect_model(self.pre_fx_data)
        self.main_window.insert_tabs(self.sweep_page, self.feature_page, self.plot_page)
        self.main_window.create_main_menu_bar(self.pre_fx_controller)

        # initialize default data
        self.pre_fx_data.set_default_stimulus_ontology()
        self.pre_fx_data.set_default_qc_criteria()


    def run(self):
        self.main_window.show()
        return self.app_cntxt.app.exec_()


if __name__ == '__main__':
    import logging; logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", help="output path for manual states")
    args = parser.parse_args()

    app = Application(args.output_dir)

    exit_code = app.run()
    sys.exit(exit_code)





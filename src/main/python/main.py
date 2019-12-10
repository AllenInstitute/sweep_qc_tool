import sys
from pathlib import Path
import argparse
import os

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

from sweep import SweepTableView, SweepTableModel, SweepPlotConfig
from pre_fx_data import PreFxData
from fx_data import FxData
from pre_fx_controller import PreFxController
from cell_features import FeaturePage

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

    def __init__(self, sweep_plot_config: SweepPlotConfig):
        """ Holds and displays a table view (and associated model) containing 
        information about individual sweeps. 
        """

        super().__init__()

        self.sweep_view = SweepTableView(self.colnames)
        self.sweep_model = SweepTableModel(self.colnames, sweep_plot_config)

        self.sweep_view.setModel(self.sweep_model)

        layout = QVBoxLayout()
        layout.addWidget(self.sweep_view)
        self.setLayout(layout)

        self.sweep_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sweep_view.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def connect(self, data: PreFxData):
        """ Attach this component to others via signals and slots

        Parameters
        ----------
        data : 
            Will be used as the underlying data store (via this object's model).

        """

        self.sweep_model.connect(data)


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


    def insert_tabs(
        self, 
        sweep_page: SweepPage, 
        feature_page: FeaturePage, 
        plot_page: PlotPage
    ):
        """ Setup tabs for this window's central viewport.

        Parameters
        ----------
        sweep_page : 
            Displays a table of sweeps and allows users to enter manual QC values.
        feature_page : 
            Displays a table of cell-scale features.
        plot_page : 
            Displays plots which describe the cell's response to various stimulus categories.

        """

        self.centralWidget().insertTab(0, sweep_page, "Sweeps")
        self.centralWidget().insertTab(1, feature_page, "Features")
        self.centralWidget().insertTab(2, plot_page, "Plots")

    def create_main_menu_bar(self, pre_fx_controller: PreFxController):
        """ Set up the main application menu.

        Parameters
        ----------
        pre_fx_controller : 
            Owns QActions for loading nwb data, stimulus ontologies, and qc criteria

        """

        self.main_menu_bar = self.menuBar()
        self.file_menu = self.main_menu_bar.addMenu("File")
        self.edit_menu = self.main_menu_bar.addMenu("Edit")
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

        self.edit_menu.addAction(pre_fx_controller.run_feature_extraction_action)




class Application(object):

    def __init__(
        self, 
        output_dir: str, 
        backup_experiment_start_index: int, 
        experiment_baseline_start_index: int, 
        experiment_baseline_end_index: int, 
        test_plot_duration: float, 
        test_pulse_baseline_samples: int,
        experiment_plot_bessel_order: int,
        experiment_plot_bessel_critical_frequency: float,
        thumbnail_step: int
    ):
        self.app_cntxt = ApplicationContext()

        sweep_plot_config = SweepPlotConfig(
            test_plot_duration,
            test_pulse_baseline_samples,
            backup_experiment_start_index,
            experiment_baseline_start_index, 
            experiment_baseline_end_index,
            experiment_plot_bessel_order,
            experiment_plot_bessel_critical_frequency,
            thumbnail_step
        )

        # initialize components
        self.main_window = MainWindow()
        self.pre_fx_controller: PreFxController = PreFxController()
        self.pre_fx_data: PreFxData = PreFxData()
        self.fx_data: FxData = FxData()
        self.sweep_page = SweepPage(sweep_plot_config)
        self.feature_page = FeaturePage()
        self.plot_page = PlotPage()
        self.status_bar = self.main_window.statusBar()
        # set cmdline params
        self.pre_fx_controller.set_output_path(output_dir)

        # connect components
        self.pre_fx_controller.connect(self.pre_fx_data, self.fx_data)
        self.sweep_page.connect(self.pre_fx_data)
        self.main_window.insert_tabs(self.sweep_page, self.feature_page, self.plot_page)
        self.main_window.create_main_menu_bar(self.pre_fx_controller)
        self.fx_data.connect(self.pre_fx_data)
        self.feature_page.connect(self.fx_data)

        self.fx_data.status_message.connect(self.status_bar.showMessage)
        self.fx_data.status_message.connect(self.status_bar.repaint)
        self.pre_fx_data.status_message.connect(self.status_bar.showMessage)
        self.pre_fx_data.status_message.connect(self.status_bar.repaint)

        # initialize default data
        self.pre_fx_data.set_default_stimulus_ontology()
        self.pre_fx_data.set_default_qc_criteria()


    def run(self):
        self.main_window.show()
        return self.app_cntxt.app.exec_()


if __name__ == '__main__':
    import logging; logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", default=os.getcwd(), type=str, help="output path for manual states")
    parser.add_argument("--backup_experiment_start_index", type=int, default=5000,
        help="when plotting experiment pulses, where to set the start index if it is erroneously stored as <= 0"
    )
    parser.add_argument("--experiment_baseline_start_index", type=int, default=5000,
        help="when plotting experiment pulses, where to start the baseline assessment epoch"
    )
    parser.add_argument("--experiment_baseline_end_index", type=int, default=9000,
        help="when plotting experiment pulses, where to end the baseline assessment epoch"
    )
    parser.add_argument("--test_plot_duration", type=float, default=0.1,
        help="in seconds, the amount of time to use as the test pulse plot's domain"
    )
    parser.add_argument("--test_pulse_baseline_samples", type=int, default=100,
        help="when plotting test pulses, how many samples to use for baseline assessment"
    )
    parser.add_argument("--experiment_plot_bessel_order", type=int, default=4,
        help="when plotting sweep voltage traces for the experiment epoch a lowpass bessel filter is applied to the trace. This parameter defines the order of that filter."
    )
    parser.add_argument("--experiment_plot_bessel_critical_frequency", type=float, default=0.1, 
        help="when plotting sweep voltage traces for the experiment epoch a lowpass bessel filter is applied to the trace. This parameter defines the critical frequency of that filter."
    )
    parser.add_argument("--thumbnail_step", type=float, default=300, 
        help="step size for generating decimated thumbnail images for individual sweeps."
    )
    args = parser.parse_args()

    app = Application(**args.__dict__)

    exit_code = app.run()
    sys.exit(exit_code)





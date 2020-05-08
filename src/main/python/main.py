import sys
import argparse
import os
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QTabWidget,
    QGraphicsView,
    QHeaderView,
    QVBoxLayout,
    QLabel,
)
from pyqtgraph import setConfigOption

from fbs_runtime.application_context.PyQt5 import ApplicationContext

from sweep_table_view import SweepTableView
from sweep_table_model import SweepTableModel
from sweep_plotter import SweepPlotConfig
from pre_fx_data import PreFxData
from fx_data import FxData
from pre_fx_controller import PreFxController
from cell_feature_page import CellFeaturePage


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
        information about individual sweeps. Filteres out sweeps based on
        certain stimulus codes when checkboxes are ticked/unticked
        """

        super().__init__()
        # abstract model of the sweep table that is represented by sweep_view
        self.sweep_model = SweepTableModel(self.colnames, sweep_plot_config)

        # view of the sweep table that the user sees
        self.sweep_view = SweepTableView(self.colnames)
        self.sweep_view.setModel(self.sweep_model)

        # page layout
        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.sweep_view)
        self.setLayout(vbox_layout)

        self.sweep_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sweep_view.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def connect(self, data: PreFxData):
        """ Attach this component to others via signals and slots

        Parameters
        ----------
        data : 
            Will be used as the underlying data store (via this object's model).

        """
        # connect model to default checkbox states for view menu
        self.sweep_model.new_data.connect(self.set_default_filter_states)

        # connect model to raw data
        self.sweep_model.connect(data)

    def set_default_filter_states(self):
        """ Sets the default checkbox states when a new data set is loaded """
        # enable checkboxes when data is loaded
        self.sweep_view.filter_auto_qc_sweeps_action.setEnabled(True)
        self.sweep_view.filter_channel_sweeps_action.setEnabled(True)

        # set default check states
        self.sweep_view.filter_auto_qc_sweeps_action.setChecked(True)
        self.sweep_view.filter_channel_sweeps_action.setChecked(False)


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
        self.resize(1000, 1000)

        # Create tab widget & set tabs as a central widget
        tab_widget = QTabWidget()
        self.setCentralWidget(tab_widget)

        # initialize main menu bar
        self.main_menu_bar = self.menuBar()
        self.file_menu = self.main_menu_bar.addMenu("File")
        self.edit_menu = self.main_menu_bar.addMenu("Edit")
        self.settings_menu = self.main_menu_bar.addMenu("Settings")
        self.view_menu = self.main_menu_bar.addMenu("View")
        self.main_menu_bar.addMenu("Help")

    def insert_tabs(
        self, 
        sweep_page: SweepPage, 
        feature_page: CellFeaturePage, 
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

    def add_menu_actions(
            self, pre_fx_controller: PreFxController, sweep_page: SweepPage
    ):
        """ Set up the main application menu.

        Parameters
        ----------
        pre_fx_controller : PreFxController
            Owns QActions for loading nwb data, stimulus ontologies, and qc criteria
        sweep_page : SweepPage
            Owns QActions for filtering the sweeps viewed on the sweep page

        """

        # add file menu actions
        self.file_menu.addAction(
            pre_fx_controller.load_data_set_action
        )
        self.file_menu.addAction(pre_fx_controller.load_data_set_lims_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(pre_fx_controller.export_manual_states_to_json_action)
        self.file_menu.addAction(pre_fx_controller.export_manual_states_to_lims_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(
            pre_fx_controller.load_stimulus_ontology_action
        )
        self.file_menu.addSeparator()
        self.file_menu.addAction(
            pre_fx_controller.load_qc_criteria_action
        )

        # add settings menu actions
        self.settings_menu.addAction(pre_fx_controller.show_stimulus_ontology_action)
        self.settings_menu.addAction(pre_fx_controller.show_qc_criteria_action)

        # add edit menu actions
        self.edit_menu.addAction(pre_fx_controller.run_feature_extraction_action)

        # add view menu actions
        self.view_menu.addAction(sweep_page.sweep_view.filter_auto_qc_sweeps_action)
        self.view_menu.addAction(sweep_page.sweep_view.filter_channel_sweeps_action)

    def setup_status_bar(self, pre_fx_data: PreFxData, fx_data: FxData):
        """ Sets up a status bar, which reports the current state of the app. 
        Connects this status bar to the underlying models
        """

        fx_status = QLabel(self)
        fx_status.setText("<font color='red'>cell features are outdated</font>")
        fx_status.hide()

        status_bar = self.statusBar()
        status_bar.addPermanentWidget(fx_status)

        pre_fx_data.status_message.connect(status_bar.showMessage)
        pre_fx_data.status_message.connect(status_bar.repaint)

        fx_data.status_message.connect(status_bar.showMessage)
        fx_data.status_message.connect(status_bar.repaint)
        fx_data.state_outdated.connect(fx_status.show)
        fx_data.new_state_set.connect(fx_status.hide)


class Application(object):

    def __init__(
        self, 
        output_dir: str, 
        backup_experiment_start_index: int, 
        experiment_baseline_start_index: int, 
        experiment_baseline_end_index: int, 
        test_pulse_plot_start: float,
        test_pulse_plot_end: float, 
        test_pulse_baseline_samples: int,
        thumbnail_step: int,
        initial_nwb_path: Optional[str],
        initial_stimulus_ontology_path: Optional[str],
        initial_qc_criteria_path: Optional[str]
    ):
        self.app_cntxt = ApplicationContext()

        sweep_plot_config = SweepPlotConfig(
            test_pulse_plot_start,
            test_pulse_plot_end,
            test_pulse_baseline_samples,
            backup_experiment_start_index,
            experiment_baseline_start_index, 
            experiment_baseline_end_index,
            thumbnail_step
        )

        # initialize components
        self.main_window = MainWindow()
        self.pre_fx_controller: PreFxController = PreFxController()
        self.pre_fx_data: PreFxData = PreFxData()
        self.fx_data: FxData = FxData()
        self.sweep_page = SweepPage(sweep_plot_config)
        self.feature_page = CellFeaturePage()
        self.plot_page = PlotPage()
        self.status_bar = self.main_window.statusBar()

        # set cmdline params
        self.pre_fx_controller.set_output_path(output_dir)

        # connect components
        # connect controller toraw data and feature extractor
        self.pre_fx_controller.connect(self.pre_fx_data, self.fx_data)
        # connect sweep page to raw data
        self.sweep_page.connect(self.pre_fx_data)
        # connect main window to various components
        self.main_window.insert_tabs(self.sweep_page, self.feature_page, self.plot_page)
        self.main_window.add_menu_actions(self.pre_fx_controller, self.sweep_page)
        # connect feature extractor to raw data
        self.fx_data.connect(self.pre_fx_data)
        # connect feature page to feature extractor
        self.feature_page.connect(self.fx_data)

        # initialize status bar
        self.main_window.setup_status_bar(self.pre_fx_data, self.fx_data)
        # initialize default data
        self.pre_fx_data.set_default_stimulus_ontology()
        self.pre_fx_data.set_default_qc_criteria()

        # The user can request that specific data be loaded on start
        if initial_stimulus_ontology_path is not None:
            self.pre_fx_controller.selected_stimulus_ontology_path.emit(initial_stimulus_ontology_path)
        if initial_qc_criteria_path is not None:
            self.pre_fx_controller.selected_qc_criteria_path.emit(initial_qc_criteria_path)
        if initial_nwb_path is not None:
            self.pre_fx_controller.selected_data_set_path.emit(initial_nwb_path)

    def run(self):
        self.main_window.show()
        return self.app_cntxt.app.exec_()


if __name__ == '__main__':
    import logging; logging.getLogger().setLevel(logging.INFO)

    setConfigOption("background", "w")

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
    parser.add_argument("--test_pulse_plot_start", type=float, default=0.04,
        help="where in time (s) to start the test pulse plot"
    )
    parser.add_argument("--test_pulse_plot_end", type=float, default=0.1,
        help="in seconds, the end time of the test pulse plot's domain"
    )
    parser.add_argument("--test_pulse_baseline_samples", type=int, default=100,
        help="when plotting test pulses, how many samples to use for baseline assessment"
    )
    parser.add_argument("--thumbnail_step", type=float, default=20, 
        help="step size for generating decimated thumbnail images for individual sweeps."
    )
    parser.add_argument("--initial_nwb_path", type=str, default=None, 
        help="upon start, immediately load an nwb file from here"
    )
    parser.add_argument("--initial_stimulus_ontology_path", type=str, default=None,
        help="upon start, immediately load a stimulus ontology from here"
    )
    parser.add_argument("--initial_qc_criteria_path", type=str, default=None,
        help="upon start, immediately load qc criteria from here"
    )

    args = parser.parse_args()

    app = Application(**args.__dict__)

    exit_code = app.run()
    sys.exit(exit_code)

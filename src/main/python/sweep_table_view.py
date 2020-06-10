from typing import Optional

from PyQt5.QtWidgets import QTableView, QDialog, QGridLayout, QWidget, QAction
from PyQt5.QtCore import QModelIndex

from delegates import SvgDelegate, ComboBoxDelegate
from sweep_table_model import SweepTableModel


class SweepTableView(QTableView):

    @property
    def colnames(self):
        return self._colnames

    @colnames.setter
    def colnames(self, names):
        self._colnames = names
        self._idx_colname_map = {}
        self._colname_idx_map = {}
        
        for idx, name in enumerate(self._colnames):
            self._idx_colname_map[idx] = name
            self._colname_idx_map[name] = idx

    def __init__(self, colnames):
        super().__init__()
        self.colnames = colnames

        self.svg_delegate = SvgDelegate()
        manual_qc_choices = ["default", "failed", "passed"]
        self.cb_delegate = ComboBoxDelegate(self, manual_qc_choices)

        self.setItemDelegateForColumn(self.colnames.index("test epoch"), self.svg_delegate)
        self.setItemDelegateForColumn(self.colnames.index("experiment epoch"), self.svg_delegate)
        self.setItemDelegateForColumn(self.colnames.index("manual QC state"), self.cb_delegate)

        self.verticalHeader().setMinimumSectionSize(120)

        self.clicked.connect(self.on_clicked)

        self.setWordWrap(True)

        # sweep view filter actions
        self.view_all_sweeps = QAction("All sweeps")
        # current / voltage clamp
        self.view_v_clamp = QAction("Voltage clamp")
        self.view_i_clamp = QAction("Current clamp")
        # stimulus codes
        self.view_pipeline = QAction("QC Pipeline")
        self.view_ex_tp = QAction("EXTP - Test sweeps")
        self.view_nuc_vc = QAction("NucVC - Channel recordings")
        self.view_core_one = QAction("Core 1")
        self.view_core_two = QAction("Core 2")
        # qc status
        self.view_auto_pass = QAction("Auto passed")
        self.view_auto_fail = QAction("Auto failed")
        self.view_no_auto_qc = QAction("No auto QC")
        # initialize these actions
        self.init_actions()

        # initializing sets of sweeps for sweep filtering purposes
        self.all_sweeps = Optional[set]
        self.visible_sweeps = set()
        self.hidden_sweeps = set()

    def init_actions(self):
        """ Initializes menu actions which are responsible for filtering sweeps
        """
        # initialize view all sweeps action
        self.view_all_sweeps.setCheckable(True)
        self.view_all_sweeps.triggered.connect(self.filter_sweeps)
        self.view_all_sweeps.setEnabled(False)

        # initialize filter down to auto qc action
        self.view_pipeline.setCheckable(True)
        self.view_pipeline.triggered.connect(self.filter_sweeps)
        self.view_pipeline.setEnabled(False)

        # initialize filter down to channel sweeps action
        self.view_nuc_vc.setCheckable(True)
        self.view_nuc_vc.triggered.connect(self.filter_sweeps)
        self.view_nuc_vc.setEnabled(False)

    def get_column_index(self, name: str) -> Optional[int]:
        return self._colname_idx_map.get(name, None)
    
    def get_index_column(self, index: int) -> Optional[str]:
        return self._idx_colname_map.get(index, None)

    def setModel(self, model: SweepTableModel):
        """ Attach a SweepTableModel to this view. The model will provide data for 
        this view to display.
        """
        super(SweepTableView, self).setModel(model)
        model.rowsInserted.connect(self.persist_qc_editor)
        model.rowsInserted.connect(self.resize_to_content)

    def resize_to_content(self, *args, **kwargs):
        """ This function just exists so that we can connect signals with 
        extraneous data to resizeRowsToContents
        """

        self.resizeRowsToContents()

    def resizeEvent(self, *args, **kwargs):
        """ Makes sure that we resize the rows to their contents when the user
        resizes the window
        """

        super(SweepTableView, self).resizeEvent(*args, **kwargs)
        self.resize_to_content()

    def persist_qc_editor(self, *args, **kwargs):
        """ Ensure that the QC state editor can be opened with a single click.

        Parameters
        ----------
        All are ignored. They are present because this method is triggered
        by a data-carrying signal.

        """

        column = self.colnames.index("manual QC state")

        for row in range(self.model().rowCount()):
            self.openPersistentEditor(self.model().index(row, column))

    def on_clicked(self, index: QModelIndex):
        """ When plot thumbnails are clicked, open a larger plot in a popup.

        Parameters
        ----------
        index : 
            Which plot to open. The popup will be mopved to this item's location.

        """

        test_column = self.get_column_index("test epoch")
        exp_column = self.get_column_index("experiment epoch")

        if not index.column() in {test_column, exp_column}:
            return

        # display popup plot at (100, 100) for user convenience
        self.popup_plot(self.model().data(index).full(), left=100, top=100)

    def popup_plot(self, graph: QWidget, left: int = 0, top: int = 0):
        """ Make a popup with a single widget, which ought to be a plotter for 
        the full experiment or test pulse plots.

        Parameters
        ----------
        graph : a widget to be displayed in the popup
        left : left position at which the popup will be placed (px)
        top : top position at which the popup will be placed (px)

        """

        popup = QDialog()
        layout = QGridLayout()
        
        layout.addWidget(graph)
        popup.setLayout(layout)
        popup.move(left, top)
        popup.exec()

    def update_sweep_view(self):
        visible_sweep_codes: list = ['foo']
        hidden_sweep_codes: list = ['bar']

        for index, row in enumerate(self.model().sweep_features):
            if row['stimulus_code'] in visible_sweep_codes:
                self.showRow(index)
            elif row['stimulus_code'] in hidden_sweep_codes:
                self.hideRow(index)

    def filter_sweeps(self):
        """ Filters the table down to sweeps based on the checkboxes that are
        check in the view menu. If 'Auto QC sweeps' is checked then it will
        only show sweeps that have gone through the auto QC pipeline. If
        'Channel recording sweeps' is checked then it will only show channel
        recording sweeps with the 'NucVC' prefix. If both are checked then
        it will only show auto QC pipeline sweeps and channe
        l recording sweeps.
        If neither are checked it will show everything except 'Search' sweeps.

        """
        # temporary variable of visible sweeps
        visible_sweeps = set()
        # add checked view options to set of visible sweeps
        # all sweeps
        if self.view_all_sweeps.isChecked():
            visible_sweeps.update(self.model().sweep_types['all_sweeps'])
        # pipeline sweeps
        if self.view_pipeline.isChecked():
            visible_sweeps.update(self.model().sweep_types['pipeline'])
        # channel recording sweeps
        if self.view_nuc_vc.isChecked():
            visible_sweeps.update(self.model().sweep_types['nuc_vc'])

        # remove 'Search' sweeps from visible sweeps
        visible_sweeps = visible_sweeps - self.model().sweep_types['search']

        # loop through rows of table model and show only visible sweeps
        for index in range(self.model().rowCount()):
            if index in visible_sweeps:
                self.showRow(index)
            else:
                self.hideRow(index)

        # # if both are checked, then show auto QC and channel sweeps
        # if self.view_pipeline.isChecked() \
        #         and self.view_nuc_vc.isChecked():
        #     for index in range(self.model().rowCount()):
        #         if index in self.model().sweep_types['pipeline'].union(
        #             self.model().sweep_types['nuc_vc']
        #         ):
        #             self.showRow(index)
        #         else:
        #             self.hideRow(index)
        #
        # # if only auto QC is checked, then only show auto QC
        # elif self.view_pipeline.isChecked():
        #     for index in range(self.model().rowCount()):
        #         if index in self.model().sweep_types['pipeline']:
        #             self.showRow(index)
        #         else:
        #             self.hideRow(index)
        #
        # # if only channel sweeps are checked, then only show channel sweeps
        # elif self.view_nuc_vc.isChecked():
        #     for index in range(self.model().rowCount()):
        #         if index in self.model().sweep_types['nuc_vc']:
        #             self.showRow(index)
        #         else:
        #             self.hideRow(index)
        #
        # # if neither are checked, then show everything except for 'Search'
        # else:
        #     for index in range(self.model().rowCount()):
        #         if index not in self.model().sweep_types['search']:
        #             self.showRow(index)
        #         else:
        #             self.hideRow(index)

    def show_v_clamp(self):
        self.visible_sweeps.update(self.model().sweep_types['v_clamp'])

    def show_i_clamp(self):
        """ Show current clamp sweeps. """
        self.visible_sweeps.update(self.model().sweep_types['i_clamp'])

    def show_pipeline(self):
        self.visible_sweeps.update(self.model().sweep_types['pipeline'])

    def show_search(self):
        self.visible_sweeps.update(self.model().sweep_types['search'])

    def show_ex_tp(self):
        self.visible_sweeps.update(self.model().sweep_types['ex_tp'])

    def show_nuc_vc(self):
        self.visible_sweeps.update(self.model().sweep_types['nuv_vc'])

    def show_core_one(self):
        self.visible_sweeps.update(self.model().sweep_types['core_one'])

    def show_core_two(self):
        self.visible_sweeps.update(self.model().sweep_types['core_two'])

    def show_unkown(self):
        self.visible_sweeps.update(self.model().sweep_types['unknown'])

    def show_auto_pass(self):
        """ Show sweeps that passed all auto qc. """
        self.visible_sweeps.update(self.model().sweep_types['auto_pass'])

    def show_auto_fail(self):
        """ Show sweeps that failed auto qc at some point. """
        self.visible_sweeps.update(self.model().sweep_types['auto_fail'])

    def show_no_auto_qc(self):
        """ Show sweeps that are not 'Search' or part of auto-qc pipeline. """
        self.visible_sweeps.update(self.model().sweep_types['no_auto_qc'])

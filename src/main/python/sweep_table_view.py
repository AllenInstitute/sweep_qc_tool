from typing import Optional

from PyQt5.QtWidgets import QTableView, QWidget, QAction
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
        # A list of active popup plots to show when thumbnails are clicked
        self.popup_plots = []

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
        # view qc pipeline sweeps
        self.view_pipeline = QAction("QC Pipeline")
        # view channel recording sweeps
        self.view_nuc_vc = QAction("NucVC - Channel recordings")

        # initialize these actions
        self.init_actions()

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
        # add the graph to list of active popup plots
        self.popup_plots.append(graph)

        # remove the oldest popup plots if there are more than 5
        while len(self.popup_plots) > 5:
            self.popup_plots.pop(0)

        # the great-great-grandparent of this widget should be the main window
        main_window = self.parent().parent().parent().parent()

        # move popup plot to nice location relative to main window
        graph.window().move(
            left + main_window.pos().x(),
            top + main_window.pos().y()
        )
        graph.show()

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

        # set view pipeline to checked if it is a subset of visible sweeps
        self.view_pipeline.setChecked(
            self.model().sweep_types['pipeline'].issubset(visible_sweeps)
        )
        # set view nuc vc to checked if it is a subset of visible sweeps
        self.view_nuc_vc.setChecked(
            self.model().sweep_types['nuc_vc'].issubset(visible_sweeps)
        )

        # loop through rows of table model and show only visible sweeps
        for index in range(self.model().rowCount()):
            if index in visible_sweeps:
                self.showRow(index)
            else:
                self.hideRow(index)

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
        self.filter_auto_qc_sweeps_action = QAction("Auto QC sweeps")
        self.filter_channel_sweeps_action = QAction("Channel recording sweeps")
        self.init_actions()

    def init_actions(self):
        """ Initializes menu actions which are responsible for filtering sweeps
        """
        # initialize filter down to auto qc action
        self.filter_auto_qc_sweeps_action.setCheckable(True)
        self.filter_auto_qc_sweeps_action.toggled.connect(self.filter_sweeps)
        self.filter_auto_qc_sweeps_action.setEnabled(False)

        # initialize filter down to channel sweeps action
        self.filter_channel_sweeps_action.setCheckable(True)
        self.filter_channel_sweeps_action.toggled.connect(self.filter_sweeps)
        self.filter_channel_sweeps_action.setEnabled(False)

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
        all are ignored. They are present because this method is triggered by a data-carrying signal

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

    def filter_sweeps(self):
        """ Filters the table down to sweeps based on the checkboxes that are
        check in the view menu. If 'Auto QC sweeps' is checked then it will
        only show sweeps that have gone through the auto QC pipeline. If
        'Channel recording sweeps' is checked then it will only show channel
        recording sweeps with the 'NucVC' prefix. If both are checked then
        it will only show auto QC pipeline sweeps and channel recording sweeps.
        If neither are checked it will show everything except 'Search' sweeps.

        """
        # if both are checked, then show auto QC and channel sweeps
        if self.filter_auto_qc_sweeps_action.isChecked() \
                and self.filter_channel_sweeps_action.isChecked():
            for index, row in enumerate(self.model().sweep_features):
                if row['passed'] is not None \
                        or row['stimulus_code'][0:5] == "NucVC":
                    self.showRow(index)
                else:
                    self.hideRow(index)

        # if only auto QC is checked, then only show auto QC
        elif self.filter_auto_qc_sweeps_action.isChecked():
            for index, row in enumerate(self.model().sweep_features):
                if row['passed'] is not None:
                    self.showRow(index)
                else:
                    self.hideRow(index)

        # if only channel sweeps are checked, then only show channel sweeps
        elif self.filter_channel_sweeps_action.isChecked():
            for index, row in enumerate(self.model().sweep_features):
                if row['stimulus_code'][0:5] == "NucVC":
                    self.showRow(index)
                else:
                    self.hideRow(index)

        # if neither are checked then show everything except for 'Search'
        else:
            for index, row in enumerate(self.model().sweep_features):
                if row['stimulus_code'][-6:] != "Search":
                    self.showRow(index)
                else:
                    self.hideRow(index)

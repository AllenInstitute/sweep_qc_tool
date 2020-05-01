from typing import Optional


from PyQt5.QtWidgets import QTableView, QDialog, QGridLayout, QWidget
from PyQt5.QtCore import QModelIndex, Qt

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
        all are ignored. They are present because this method is triggered by a data-carrying signal.

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

        index_rect = self.visualRect(index)
        self.popup_plot(
            self.model().data(index).full(),
            index_rect.left(),
            index_rect.top()
        )

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

    def filter_auto_qc(self, state):
        """ Filters the table down to sweeps that went through auto QC pipeline
        if the button is checked

        Parameters
        ----------
            state : the state that the button is in (check/unchecked)
        """
        if state == Qt.Checked:
            print('Checked')
        else:
            print('Unchecked')

from PyQt5.QtWidgets import QTableView, QDialog, QGridLayout
from PyQt5.QtCore import QModelIndex

from pyqtgraph import mkPen, PlotWidget

from delegates import SvgDelegate, ComboBoxDelegate
from sweep_table_model import SweepTableModel


class SweepTableView(QTableView):

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
        
        if not hasattr(self.model(), "column_map"):
            return
        column_map = self.model().column_map

        if not index.column() in {column_map["test epoch"], column_map["experiment epoch"]}:
            return

        time, voltage, baseline = self.model().data(index).full
        index_rect = self.visualRect(index)        

        graph = PlotWidget()
        item = graph.getPlotItem()
        item.plot(time, voltage, pen=mkPen(color="k", width=2))
        item.addLine(y=baseline, pen=mkPen(color="b", width=2))


        popup = QDialog()
        layout = QGridLayout()
        
        layout.addWidget(graph)
        popup.setLayout(layout)
        popup.move(index_rect.left(), index_rect.top())
        popup.exec()

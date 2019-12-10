from typing import List

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLayout, QLayoutItem, QSizePolicy, QStyle, QFrame, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt, QRect, QSize, QMargins, QPoint

from fx_data import FxData


class FeaturePage(QScrollArea):


    def __init__(self):
        super().__init__()

        unit_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        self.central = QWidget()
        self.central_layout = QVBoxLayout()

        self.central.setLayout(self.central_layout)
        scroll_area.setWidget(self.central)
        unit_layout.addWidget(scroll_area)
        self.setLayout(unit_layout)
        
        self.central_layout.setSpacing(22)

        scroll_area.setWidgetResizable(True)
        scroll_area.setEnabled(True)


    def connect(self, fx_data: FxData):
        fx_data.state_outdated.connect(self.clear)
        fx_data.new_state_set.connect(self.on_new_data)


    def clear(self):
        for ii in range(self.central_layout.count() - 1, -1, -1):
            widget_item = self.central_layout.takeAt(ii)
            
            if widget_item is not None:
                widget = widget_item.widget()
            
            # we want the widget to be garbage collected (and to be invisible until then)
            widget.setParent(None)
            widget.hide()

    def on_new_data(self, data):
        self.clear()

        show = FeaturePage.to_show()

        for ii, (category, keys) in enumerate(show.items()):
            current_widget = QWidget()
            current_layout = FlowLayout(11, 11, 11)

            for key in keys:
                current_layout.addWidget(CellFeature(
                    key, get_feature(data, *["cell_record", key])
                ))

            current_widget.setLayout(current_layout)
            self.central_layout.addWidget(current_widget)

            if ii < len(show) - 1:
                divider = QFrame()
                divider.setFrameStyle(QFrame.HLine)
                divider.setLineWidth(3)
                self.central_layout.addWidget(divider)


    @classmethod
    def to_show(cls):
        return {
            "general": [
                "adaptation",
                "avg_isi",
                "blowout_mv",
                "electrode_0_pa",
                "f_i_curve_slope",
                "rheobase_sweep_num",
                "ri",
                "sag",
                "seal_gohm",
                "tau",
                "thumbnail_sweep_num",
                "vm_for_sag",
                "vrest",
            ],
            "fast_trough": [
                "fast_trough_t_long_square",
                "fast_trough_t_ramp",
                "fast_trough_t_short_square",
                "fast_trough_v_long_square",
                "fast_trough_v_ramp",
                "fast_trough_v_short_square",
            ],
            "slow_trough": [
                "slow_trough_t_long_square",
                "slow_trough_t_ramp",
                "slow_trough_t_short_square",
                "slow_trough_v_long_square",
                "slow_trough_v_ramp",
                "slow_trough_v_short_square",
            ],
            "threshold": [
                "threshold_i_long_square",
                "threshold_i_ramp",
                "threshold_i_short_square",
                "threshold_t_long_square",
                "threshold_t_ramp",
                "threshold_t_short_square",
                "threshold_v_long_square",
                "threshold_v_ramp",
                "threshold_v_short_square",
            ],
            "trough": [
                "trough_t_long_square",
                "trough_t_ramp",
                "trough_t_short_square",
                "trough_v_long_square",
                "trough_v_ramp",
                "trough_v_short_square",
            ],
            "peak": [
                "peak_t_long_square",
                "peak_t_ramp",
                "peak_t_short_square",
                "peak_v_long_square",
                "peak_v_ramp",
                "peak_v_short_square",
            ],
            "upstroke_downstroke_ratio": [
                "upstroke_downstroke_ratio_long_square",
                "upstroke_downstroke_ratio_ramp",
                "upstroke_downstroke_ratio_short_square",
            ],
            "resistance": [
                "initial_access_resistance_mohm",
                "input_access_resistance_ratio",
                "input_resistance_mohm",
            ]
        }



def get_feature(data, *path):
    for key in path:
        data = data.get(key, None)
    return format_feature(data)
    

def format_feature(feature):
    if isinstance(feature, float):
        return "%.3f" % feature
    if isinstance(feature, int):
        return "%d" % feature
    return str(feature)






class CellFeature(QFrame):

    def __init__(self, key, value, *args, **kwargs):
        super(CellFeature, self).__init__(*args, **kwargs)
        self.setFrameStyle(QFrame.WinPanel | QFrame.Raised)

        key_label = QLabel()
        key_label.setText(f"{key}")
        key_label.setAlignment(Qt.AlignCenter)

        divider = QFrame()
        divider.setFrameStyle(QFrame.HLine)

        value_label = QLabel()
        value_label.setText(value)
        value_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(key_label)
        layout.addWidget(divider)
        layout.addWidget(value_label)
        self.setLayout(layout)


class FlowLayout(QLayout):


    def __init__(
        self, 
        margin: int, 
        horizontal_spacing: int, 
        vertical_spacing: int
    ):
        super(FlowLayout, self).__init__()

        self.items: List[QLayoutItem] = []

        self.vertical_spacing = vertical_spacing
        self.horizontal_spacing = horizontal_spacing

        self.setContentsMargins(margin, margin, margin, margin)

    def clear(self):
        self.items =  []

    def horizontalSpacing(self):
        return self.horizontal_spacing

    def verticalSpacing(self):
        return self.vertical_spacing

    def addItem(self, item):
        self.items.append(item)
    
    def count(self) -> int:
        return len(self.items)

    def itemAt(self, index: int):
        if index >= len(self.items):
            return
        return self.items[index]

    def takeAt(self, index: int):
        return self.items.pop(index)

    def expandingDirections(self):
        return 0

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width: int):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def expandingDirections(self):
        return Qt.Horizontal | Qt.Vertical

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size: QSize = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())

        margins: QMargins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect: QRect, testOnly: bool):
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect: QRect = rect.adjusted(left, top, -right, -bottom)
        
        x: int = effectiveRect.x()
        y: int = effectiveRect.y()
        lineHeight: int = 0

        for item in self.items:
            widget = item.widget()
            spaceX = self.horizontalSpacing()
            spaceY = self.verticalSpacing()

            if spaceX == -1:
                spaceX = widget.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            if spaceY == -1:
                spaceY = widget.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)

            nextX: int = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + bottom

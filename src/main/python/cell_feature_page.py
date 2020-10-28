""" A page for displaying grouped key-value pairs describing feature 
extraction results.
"""
from typing import Optional, Dict, List, Callable, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLayoutItem, QFrame, QScrollArea
)

from fx_data import FxData
from flow_layout import FlowLayout
from cell_feature_view import CellFeatureView


KeysType = Dict[str, List[str]]


def default_keys() -> KeysType:
    return {
        "general": [
            "adaptation",
            "avg_isi",
            "blowout_mv",
            "electrode_0_pa",
            "f_i_curve_slope",
            "rheobase_sweep_num",
            "sag",
            "tau",
            "vm_for_sag",
            "vrest",
            "thumbnail_sweep_num",
            "seal_gohm",
            "initial_access_resistance_mohm",
            "input_access_resistance_ratio",
            "input_resistance_mohm",
            "ri",
        ],
        "ramp": [
            "upstroke_downstroke_ratio_ramp",
            "fast_trough_t_ramp",
            "fast_trough_v_ramp",
            "slow_trough_t_ramp",
            "slow_trough_v_ramp",
            "threshold_t_ramp",
            "threshold_v_ramp",
            "threshold_i_ramp",
            "trough_t_ramp",
            "trough_v_ramp",
            "peak_t_ramp",
            "peak_v_ramp",
        ],
        "short_square": [
            "upstroke_downstroke_ratio_short_square",
            "fast_trough_t_short_square",
            "fast_trough_v_short_square",
            "slow_trough_t_short_square",
            "slow_trough_v_short_square",
            "threshold_t_short_square",
            "threshold_v_short_square",
            "threshold_i_short_square",
            "trough_t_short_square",
            "trough_v_short_square",
            "peak_t_short_square",
            "peak_v_short_square",
        ],
        "long_square": [
            "upstroke_downstroke_ratio_long_square",
            "fast_trough_t_long_square",
            "fast_trough_v_long_square",
            "slow_trough_t_long_square",
            "slow_trough_v_long_square",
            "threshold_t_long_square",
            "threshold_v_long_square",
            "threshold_i_long_square",
            "trough_t_long_square",
            "trough_v_long_square",
            "peak_t_long_square",
            "peak_v_long_square",
        ],
    }


class CellFeaturePage(QWidget):

    def __init__(
        self, 
        vertical_spacing: int = 22, 
        divider_width: int = 3, 
        get_keys: Callable[[], KeysType] = default_keys
    ):
        """ A scrollable widget for displaying grouped key-value pairs.

        Parameters
        ----------
        vertical_spacing : 
            How much spacing between successive groups / dividers (px)?
        divider_width : 
            How thick should dividers be (px)?
        get_keys : 
            A callable which returns grouped keys. These keys will be used to 
            extract values from fx_data

        """
        
        super().__init__()

        # this has one more layer of indirection than we would like - making 
        # the top-level widget a QScrollArea produces inconsistent styling when 
        # compared to the other pages, though
        unit_layout: QVBoxLayout = QVBoxLayout()
        scroll_area: QScrollArea = QScrollArea()
        self.central: QWidget = QWidget()
        self.central_layout: QVBoxLayout = QVBoxLayout()

        self.central.setLayout(self.central_layout)
        scroll_area.setWidget(self.central)
        unit_layout.addWidget(scroll_area)
        self.setLayout(unit_layout)
        
        self.central_layout.setSpacing(vertical_spacing)

        scroll_area.setWidgetResizable(True)
        scroll_area.setEnabled(True)

        self.divider_width = divider_width
        self.get_keys = get_keys

    def connect(self, fx_data: FxData):
        fx_data.new_state_set.connect(self.on_new_data)

    def clear(self):
        """ Remove all widgets from this layout
        """

        for ii in range(self.central_layout.count() - 1, -1, -1):
            widget_item: Optional[QLayoutItem] = self.central_layout.takeAt(ii)
            
            if widget_item is not None:
                widget: QWidget = widget_item.widget()
            
                # we want the widget to eventually be garbage collected 
                # (and to be invisible until then)
                widget.setParent(None)
                widget.hide()

    def on_new_data(self, data: Dict):
        """ Replace existing data views with updated ones drawn from provided 
        dictionary.
        """

        self.clear()

        show = self.get_keys()

        for ii, (_, keys) in enumerate(show.items()):
            current_widget = QWidget()
            current_layout = FlowLayout()

            for key in keys:
                current_layout.addWidget(CellFeatureView(
                    key, get_feature(data, *["cell_record", key])
                ))

            current_widget.setLayout(current_layout)
            self.central_layout.addWidget(current_widget)

            if ii < len(show) - 1:
                divider = QFrame()
                divider.setFrameStyle(QFrame.HLine)
                divider.setLineWidth(3)
                self.central_layout.addWidget(divider)


def get_feature(data: Dict, *path: Any) -> str:
    """ Extract an element from a potentially nested dictionary
    """

    for key in path:
        data = data.get(key, None)
    return format_feature(data)
    

def format_feature(feature, float_figures=4) -> str:
    """ Ensure that numpy and python values are formatted consistently
    """

    if type(feature).__module__ == "numpy":
        feature = feature.tolist()

    if isinstance(feature, float):
        return f"%.{float_figures}f" % feature
    if isinstance(feature, int):
        return "%d" % feature
    return str(feature)

from PyQt5.QtCore import QObject, pyqtSignal
from ipfx.sweep_props import drop_failed_sweeps
from ipfx.data_set_utils import create_data_set
from ipfx.error import FeatureError
from ipfx.data_set_features import extract_data_set_features
from error_handling import exception_message

class FxData(QObject):

    status_message = pyqtSignal(str, name="status_message")

    def __init__(self):
        super().__init__()
        self._state_out_of_date: bool = False

    def set_fx_parameters(self,
                          nwb_path,
                          ontology,
                          sweep_info,
                          cell_info,
                          ):

        self._state_out_of_date = True
        self.input_nwb_file = nwb_path
        self.ontology = ontology
        self.sweep_info = sweep_info
        self.cell_info = cell_info

    def connect(self, pre_fx_data):
        pre_fx_data.data_changed.connect(self.set_fx_parameters)

    def run_feature_extraction(self):
        self.status_message.emit("Computing features, please wait.")
        drop_failed_sweeps(self.sweep_info)
        data_set = create_data_set(sweep_info=self.sweep_info,
                                   nwb_file=self.input_nwb_file,
                                   ontology=self.ontology,
                                   api_sweeps=False)
        try:
            cell_features, sweep_features, cell_record, sweep_records = extract_data_set_features(data_set)

            cell_state = {"failed_fx": False, "fail_fx_message": None}

            self.feature_data = {'cell_features': cell_features,
                                 'sweep_features': sweep_features,
                                 'cell_record': cell_record,
                                 'sweep_records': sweep_records,
                                 'cell_state': cell_state
                                }

            self._state_out_of_date = False
            self.status_message.emit("Done computing features!")

        except (FeatureError, IndexError) as ferr:
            exception_message("Feature extraction error",
                              f"failed feature extraction",
                              ferr
                              )




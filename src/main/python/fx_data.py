from PyQt5.QtCore import QObject, pyqtSignal
from ipfx.sweep_props import drop_failed_sweeps
from ipfx.dataset.create import create_ephys_data_set
from ipfx.error import FeatureError
from ipfx.data_set_features import extract_data_set_features
from error_handling import exception_message

class FxData(QObject):

    state_outdated = pyqtSignal(name="state_outdated")
    new_state_set = pyqtSignal(dict, name="new_state_set")

    status_message = pyqtSignal(str, name="status_message")

    def __init__(self):
        super().__init__()
        self._state_out_of_date: bool = False

    def out_of_date(self):
        self.state_outdated.emit()
        self._state_out_of_date = True

    
    def new_state(self):
        self.new_state_set.emit(self.feature_data)
        self._state_out_of_date = False


    def set_fx_parameters(self,
                          nwb_path,
                          ontology,
                          sweep_info,
                          cell_info,
                          ):

        self.out_of_date()
        self.input_nwb_file = nwb_path
        self.ontology = ontology
        self.sweep_info = sweep_info
        self.cell_info = cell_info

    def connect(self, pre_fx_data):
        pre_fx_data.data_changed.connect(self.set_fx_parameters)

    def run_feature_extraction(self):
        self.status_message.emit("Computing features, please wait.")
        drop_failed_sweeps(self.sweep_info)
        data_set = create_ephys_data_set(sweep_info=self.sweep_info,
                                   nwb_file=self.input_nwb_file,
                                   ontology=self.ontology)
        try:
            cell_features, sweep_features, cell_record, sweep_records,\
                cell_state, feature_states = extract_data_set_features(data_set)

            self.feature_data = {'cell_features': cell_features,
                                 'sweep_features': sweep_features,
                                 'cell_record': cell_record,
                                 'sweep_records': sweep_records,
                                 'cell_state': cell_state,
                                 'feature_states': feature_states
                                }

            self.new_state()
            self.status_message.emit("Done computing features!")

        except (FeatureError, IndexError) as ferr:
            exception_message("Feature extraction error",
                              f"failed feature extraction",
                              ferr
                              )




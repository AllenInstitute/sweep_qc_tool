import os
from pathlib import Path
import ipfx
from PyQt5.QtCore import QObject, pyqtSignal

from ipfx.bin.run_feature_extraction import run_feature_extraction
from pre_fx_data import PreFxData
from ipfx.sweep_props import drop_failed_sweeps
from ipfx.data_set_utils import create_data_set
from ipfx.error import FeatureError
from ipfx.data_set_features import extract_data_set_features


class FxData(QObject):

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

    def run_fx(self):

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

        except (FeatureError, IndexError) as e:
            cell_state = {"failed_fx": True, "fail_fx_message": str(e)}

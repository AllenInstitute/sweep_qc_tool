import json
import logging
import os
import copy
from typing import Optional, Dict, Any
import ipfx
from PyQt5.QtCore import QObject, pyqtSignal

from ipfx.ephys_data_set import EphysDataSet
from ipfx.qc_feature_extractor import cell_qc_features, sweep_qc_features
from ipfx.qc_feature_evaluator import qc_experiment, DEFAULT_QC_CRITERIA_FILE
from ipfx.bin.run_qc import qc_summary
from ipfx.stimulus import StimulusOntology, Stimulus
from ipfx.data_set_utils import create_data_set

from error_handling import exception_message
from marshmallow import ValidationError

from schemas import PipelineInput

class PreFxData(QObject):

    stimulus_ontology_set = pyqtSignal(StimulusOntology, name="stimulus_ontology_set")
    stimulus_ontology_unset = pyqtSignal(name="stimulus_ontology_unset")

    qc_criteria_set = pyqtSignal(dict, name="qc_criteria_set")
    qc_criteria_unset = pyqtSignal(name="qc_criteria_unset")

    begin_commit_calculated = pyqtSignal(name="begin_commit_calculated")
    end_commit_calculated = pyqtSignal(name="end_commit_calculated")

    def __init__(self):
        """ Main data store for all data upstream of feature extraction. This
        includes:
            - the EphysDataSet
            - the StimulusOntology
            - the qc criteria
            - the sweep extraction results
            - the qc results
        """
        super(PreFxData, self).__init__()

        self._stimulus_ontology: Optional[StimulusOntology] = None
        self._qc_criteria: Optional[Dict] = None
        self.data_set: Optional[EphysDataSet] = None
        self.nwb_path: Optional[str] = None

    def _notifying_setter(
        self, 
        attr_name: str, 
        value: Any, 
        on_set: pyqtSignal, 
        on_unset: pyqtSignal,
        send_value: bool = False
    ):
        """ Utility for a setter that emits Qt signals when the attribute in 
        question changes state.

        Parameters
        ----------
        attr_name :
            identifies attribute to be set
        value : 
            set attribute to this value
        on_set : 
            emitted when the new value is not None
        on_unset :
            emitted when the new value is None
        send_value : 
            if True, the new value will be included in the emitted signal

        """
        setattr(self, attr_name, value)

        if value is None:
            on_unset.emit()
        else:
            if send_value:
                on_set.emit(value)
            else:
                on_set.emit()

    @property
    def stimulus_ontology(self) -> Optional[StimulusOntology]:
        return self._stimulus_ontology

    @stimulus_ontology.setter
    def stimulus_ontology(self, value: Optional[StimulusOntology]):
        self._notifying_setter(
            "_stimulus_ontology", 
            value,
            self.stimulus_ontology_set, 
            self.stimulus_ontology_unset,
            send_value=True
        )

    @property
    def qc_criteria(self) -> Optional[Dict]:
        return self._qc_criteria

    @qc_criteria.setter
    def qc_criteria(self, value: Optional[Dict]):
        self._notifying_setter(
            "_qc_criteria", 
            value,
            self.qc_criteria_set, 
            self.qc_criteria_unset,
            send_value=True
        )

    def set_default_stimulus_ontology(self):
        self.load_stimulus_ontology_from_json(
            StimulusOntology.DEFAULT_STIMULUS_ONTOLOGY_FILE
        )

    def set_default_qc_criteria(self):
        self.load_qc_criteria_from_json(DEFAULT_QC_CRITERIA_FILE)

    def load_stimulus_ontology_from_json(self, path: str):
        """ Attempts to read a stimulus ontology file from a JSON. If 
        successful (and other required data are already set), attempts to 
        run the pre-fx pipeline

        Parameters
        ----------
        path : 
            load ontology from here

        """

        try:
            with open(path, "r") as ontology_file:
                ontology_data = json.load(ontology_file)
            ontology = StimulusOntology(ontology_data)
            self.ontology_file = path

            if self.nwb_path is not None and self.qc_criteria is not None:
                self.run_extraction_and_auto_qc(
                    self.nwb_path, 
                    ontology, 
                    self.qc_criteria, 
                    commit=True
                )
            else:
                self.stimulus_ontology = ontology

        except Exception as err:
            exception_message(
                "StimulusOntology load failed",
                f"failed to load stimulus ontology file from {path}",
                err
            )

    def load_qc_criteria_from_json(self, path: str):
        """ Attempts to read qc criteria from a JSON. If successful (and other 
        required data are already set), attempts to run the pre-fx pipeline

        Parameters
        ----------
        path : 
            load criteria from here

        """

        try:
            with open(path, "r") as criteria_file:
                criteria = json.load(criteria_file)
            
            if self.nwb_path is not None and self.stimulus_ontology is not None:
                self.run_extraction_and_auto_qc(
                    self.nwb_path, 
                    self.stimulus_ontology, 
                    criteria, 
                    commit=True
                )
            else:
                self.qc_criteria = criteria

        except Exception as err:
            exception_message(
                "QC criteria load failure",
                f"failed to load qc criteria file from {path}",
                err
            )

    def load_data_set_from_nwb(self, path: str):
        """ Attempts to read an NWB file describing an experiment. Fails if 
        qc criteria or stimulus ontology not already present. Otherwise, 
        attempts to run the pre-fx pipeline.

        Parameters
        ----------
        path : 
            load dataset from here

        """

        try:
            if self.stimulus_ontology is None:
                raise ValueError("must set stimulus ontology before loading a data set!")
            elif self.qc_criteria is None:
                raise ValueError("must set qc criteria before loading a data set!")
            
            self.run_extraction_and_auto_qc(path, self.stimulus_ontology, self.qc_criteria, commit=True)

        except Exception as err:
            exception_message(
                "Unable to load NWB",
                f"failed to load NWB file from {path}",
                err
            )

    def extract_manual_sweep_states(self):
        """ Extract manual sweep states in the format schemas.ManualSweepStates
        from PreFxData
        """

        return [
            {
                "sweep_number": 25,
                "sweep_state": "failed"
            },
            {
                "sweep_number": 26,
                "sweep_state": "failed"
            },

               ]

    def save_manual_states_to_json(self, path: str):

        json_data = {
            "input_nwb_file": self.nwb_path,
            "stimulus_ontology_file": self.ontology_file,
            "manual_sweep_states": self.extract_manual_sweep_states(),
            "qc_criteria": self._qc_criteria,
            "ipfx_version": ipfx.__version__
        }

        try:
            PipelineInput().load(json_data)
            with open(path, 'w') as f:
                json.dump(json_data, f, indent=4)

        except ValidationError as err:
            exception_message(
                "Unable to save manual states to JSON",
                f"manual states data failed schema validation",
                err
            )




    def run_extraction_and_auto_qc(self, nwb_path, stimulus_ontology, qc_criteria, commit=True):

        data_set = create_data_set(
            sweep_info=None,
            nwb_file=nwb_path,
            ontology=stimulus_ontology,
            api_sweeps=True,
            h5_file=None,
            validate_stim=True
        )

        cell_features, cell_tags, sweep_features = extract_qc_features(data_set)
        cell_state, cell_features, sweep_states, sweep_features = run_qc(
            stimulus_ontology, cell_features, sweep_features, qc_criteria
        )

        if commit:
            self.begin_commit_calculated.emit()

            self.stimulus_ontology = stimulus_ontology
            self.qc_criteria = qc_criteria
            self.nwb_path = nwb_path

            self.data_set = data_set
            self.cell_features = cell_features
            self.cell_tags = cell_tags
            self.cell_state = cell_state

            self.sweep_features = sweep_features
            self.sweep_states = sweep_states

            self.end_commit_calculated.emit()


def extract_qc_features(data_set):
    cell_features, cell_tags = cell_qc_features(
        data_set,
        # manual_values=cell_qc_manual_values
    )
    sweep_features = sweep_qc_features(data_set)
    return cell_features, cell_tags, sweep_features

def run_qc(stimulus_ontology, cell_features, sweep_features, qc_criteria):
    cell_features = copy.deepcopy(cell_features)
    sweep_features = copy.deepcopy(sweep_features)

    cell_state, sweep_states = qc_experiment(
        ontology=stimulus_ontology,
        cell_features=cell_features,
        sweep_features=sweep_features,
        qc_criteria=qc_criteria
    )
    qc_summary(
        sweep_features=sweep_features, 
        sweep_states=sweep_states, 
        cell_features=cell_features, 
        cell_state=cell_state
    )

    return cell_state, cell_features, sweep_states, sweep_features 

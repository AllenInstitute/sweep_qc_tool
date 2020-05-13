import json
import logging
import copy
from typing import Optional, List, Dict, Any
import ipfx
from PyQt5.QtCore import QObject, pyqtSignal

from ipfx.ephys_data_set import EphysDataSet
from ipfx.qc_feature_extractor import cell_qc_features, sweep_qc_features
from ipfx.qc_feature_evaluator import qc_experiment, DEFAULT_QC_CRITERIA_FILE
from ipfx.bin.run_qc import qc_summary
from ipfx.stimulus import StimulusOntology
from ipfx.data_set_utils import create_data_set
from ipfx.sweep_props import drop_tagged_sweeps
from error_handling import exception_message
from marshmallow import ValidationError
from schemas import PipelineParameters


class PreFxData(QObject):

    stimulus_ontology_set = pyqtSignal(StimulusOntology, name="stimulus_ontology_set")
    stimulus_ontology_unset = pyqtSignal(name="stimulus_ontology_unset")

    qc_criteria_set = pyqtSignal(dict, name="qc_criteria_set")
    qc_criteria_unset = pyqtSignal(name="qc_criteria_unset")

    begin_commit_calculated = pyqtSignal(name="begin_commit_calculated")
    end_commit_calculated = pyqtSignal(list, list, dict, EphysDataSet, name="end_commit_calculated")

    data_changed = pyqtSignal(str, StimulusOntology, list, dict, name="data_changed")

    status_message = pyqtSignal(str, name="status_message")

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

        # Nwb related data
        self.data_set: Optional[EphysDataSet] = None
        self.nwb_path: Optional[str] = None
        # Ontology path and data
        self.ontology_file: Optional[str] = None
        self._stimulus_ontology: Optional[StimulusOntology] = None

        # QC related data
        # criteria used with auto QC
        self._qc_criteria: Optional[Dict] = None
        # manual QC states selected by the user
        self.manual_qc_states: Dict[int, str] = {}
        # QC info and states at the cell (experiment) level
        self.cell_features: Optional[dict] = None
        self.cell_tags: Optional[list] = None
        self.cell_state: Optional[dict] = None
        # QC info and states at the sweep level
        self.sweep_features: Optional[list] = None
        self.sweep_states: Optional[list] = None
        # backup copies of QC info and states
        # used if user changes manual state back to 'default
        self.initial_sweep_features: Optional[list] = None
        self.initial_sweep_states: Optional[list] = None

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
            load data set from here

        """
        try:
            if self.stimulus_ontology is None:
                raise ValueError("must set stimulus ontology before loading a data set!")
            elif self.qc_criteria is None:
                raise ValueError("must set qc criteria before loading a data set!")

            self.status_message.emit("Running extraction and auto qc...")
            self.run_extraction_and_auto_qc(
                path, self.stimulus_ontology, self.qc_criteria, commit=True
            )
            self.status_message.emit("Done running extraction and auto qc")
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
                "sweep_number": sweep["sweep_number"],
                "sweep_state": self.manual_qc_states[sweep["sweep_number"]]
            }
            for sweep in self.sweep_features
        ]

    def save_manual_states_to_json(self, filepath: str):

        json_data = {
            "input_nwb_file": self.nwb_path,
            "stimulus_ontology_file": self.ontology_file,
            "manual_sweep_states": self.extract_manual_sweep_states(),
            "qc_criteria": self._qc_criteria,
            "ipfx_version": ipfx.__version__
        }

        try:
            PipelineParameters().load(json_data)
            with open(filepath, 'w') as f:
                json.dump(json_data, f, indent=4)

        except ValidationError as valerr:
            exception_message(
                "Unable to save manual states to JSON",
                f"Manual states data failed schema validation",
                valerr
            )
        except IOError as ioerr:
            exception_message(
                "Unable to write file",
                f'Unable to write to file {filepath}',
                ioerr
            )

    def run_extraction_and_auto_qc(self, nwb_path, stimulus_ontology, qc_criteria, commit=True):
        """ Creates a data set from the nwb path;
        calculates cell features, tags, and sweep features using ipfx;
        and runs auto qc on the experiment. If commit=True (default setting),
        it creates a dictionary of default manual qc states and calls
        SweepTableModel.on_new_data(), which builds the sweep table and
        generates all the thumbnail plots.

        Parameters
        ----------
        nwb_path : str
            location of the .nwb file used to create the data set
        stimulus_ontology: StimulusOntology
            stimulus ontology object used in data set creation
        qc_criteria : dict
            dictionary of qc criteria used when running auto-qc
        commit : bool
            indicates whether or not to build new sweep table model
        """
        self.status_message.emit("Creating data set...")
        # Creates the data set using input parameters
        data_set = create_data_set(
            sweep_info=None,
            nwb_file=nwb_path,
            ontology=stimulus_ontology,
            api_sweeps=True,
            h5_file=None,
            validate_stim=True
        )

        data_set.sweep_table.sort_values(by='sweep_number', axis=0, inplace=True)

        self.status_message.emit("Performing auto QC...")
        # cell_features: dictionary of QC information about the cell
        # cell_tags: QC details about the cell (e.g. 'Blowout is not available'
        # sweep_features: list of dictionaries containing qc information for
        #   sweeps that that have gone through auto qc
        cell_features, cell_tags, pre_qc_sweep_features = extract_qc_features(data_set)

        # sweep_states: list of dictionaries containing sweep pass/fail states
        # cell_state: dictionary of qc states for the cell related to cell_features
        cell_state, cell_features, sweep_states, post_qc_sweep_features = run_qc(
            stimulus_ontology, cell_features, pre_qc_sweep_features, qc_criteria
        )

        if commit:
            self.status_message.emit("Gathering QC information...")
            self.begin_commit_calculated.emit()

            self.stimulus_ontology = stimulus_ontology
            self.qc_criteria = qc_criteria
            self.nwb_path = nwb_path

            self.data_set = data_set
            self.cell_features = cell_features
            self.cell_tags = cell_tags
            self.cell_state = cell_state

            # uses auto qc info to populate self with initial and current
            # sweep features and sweep states
            self.populate_qc_info(
                pre_qc_sweep_features=pre_qc_sweep_features,
                post_qc_sweep_features=post_qc_sweep_features,
                sweep_states=sweep_states
            )

            # initializing manual qc states as "default" for everything
            self.manual_qc_states = {
                sweep['sweep_number']: "default" for sweep in self.sweep_states
            }

            self.status_message.emit("Initializing sweep page...")
            # emits signal that tells sweep_table_model to populate itself
            # with new data
            self.end_commit_calculated.emit(
                self.sweep_features, self.sweep_states, self.manual_qc_states, self.data_set
            )

        # notifies fx_data that data has changed
        self.data_changed.emit(self.nwb_path,
                               self.stimulus_ontology,
                               self.sweep_features,
                               self.cell_features)

    def populate_qc_info(
        self,
        pre_qc_sweep_features: List[dict],
        post_qc_sweep_features: List[dict],
        sweep_states: List[dict]
    ):
        """ Uses pre and post sweep qc features to populate initial and current
        sweep QC features and states. Sweep features and states use values of
        True, False, or None to indicate their auto QC states.

         For sweep_features['passed']:
            True = Passed all auto qc
            False = Failed in second round of auto qc when run_qc() was called.
                These sweeps exist in post_qc_sweep_features
            None = Dropped in first round of auto qc due to having a fail tag
                or no auto QC was performed.
                Sweeps with None in this column are dropped before feature
                extraction so that extract_data_set_features() doesn't break.
                These sweeps exist in pre_qc_sweep_features, but do not exist
                in post_qc_sweep_features.

        For sweep_states['passed']:
            True = Passed all auto qc
            False = Failed in first or second round of auto qc.
            None = No auto QC. These sweeps exist in the sweep table, but do
                not exist in pre_qc_sweep_features or post_qc_sweep_features

        Parameters
        ----------
        pre_qc_sweep_features : List[dict]
            Contains sweep features that went through qc feature extraction.
            The ['passed'] column does not exist in this list.
        post_qc_sweep_features : List[dict]
            Contains sweep features that went through the second round of
            auto QC. Sweeps that had a fail tag in pre_qc_sweep_features are
            dropped and not present in this list.
        sweep_states : List[dict]
            Contains auto QC states obtained in the second round of auto QC
            Again, sweeps that were dropped because they had a fail tag
            are not present in this list.


        """
        num_sweeps = len(self.data_set.sweep_table)

        # initializing list of empty dicts with keys from post_qc_features
        self.sweep_features = [
            dict.fromkeys(post_qc_sweep_features[0].keys())
            for _ in range(num_sweeps)
        ]

        # initializing sweep auto qc states
        self.sweep_states = [{'passed': None, 'reasons': [], 'sweep_number': x}
                             for x in range(num_sweeps)]

        # populating sweep_features and sweep_states with
        # sweeps that made it through auto qc
        for index, row in enumerate(post_qc_sweep_features):
            self.sweep_features[row['sweep_number']] = row
            self.sweep_states[row['sweep_number']] = sweep_states[index]

        # populating sweep_features and sweep_states with
        # rows that were dropped during run_qc() (usually terminated early)
        for row in pre_qc_sweep_features:
            if self.sweep_features[row['sweep_number']]['passed'] is None:
                self.sweep_features[row['sweep_number']].update(row)
                # Leaving sweep features 'passed' = None here to distinguish sweeps
                # weeded out after first round of auto-qc
                self.sweep_states[row['sweep_number']]['passed'] = False

        # populating sweep_features and sweep_states with
        # rows that were not included in auto qc
        for index, row in self.data_set.sweep_table.iterrows():
            if self.sweep_features[index]['sweep_number'] is None:
                self.sweep_features[index].update(row)
                self.sweep_features[index]['tags'] = []
                # sweep states with no auto QC have the "None" tag for auto-qc state
                self.sweep_states[index]['reasons'] = ['No auto QC']

        # making a copy of these initial values so they can be reset if
        # user changes manual qc state away from 'default' and back
        self.initial_sweep_features = copy.deepcopy(self.sweep_features)
        self.initial_sweep_states = copy.deepcopy(self.sweep_states)

    def on_manual_qc_state_updated(self, index: int, new_state: str):
        """ Takes in new manual QC state and updates sweep_states and
        sweep features appropriately. Note that sweep features that do not get
        passed the first round of auto qc are left as none in order to avoid
        breaking feature extraction.

        Parameters:
            index : int
                Sweep number that is being updated. Used as an index when
                    addressing sweep_States and sweep_features
            new_state : str
                String specifying manual QC state "default", "passed", or "failed"
        """
        # updating manual qc states
        self.manual_qc_states[index] = new_state

        # resetting states and features to initial values if user selected "default" again
        if new_state == "default":
            self.sweep_states[index] = copy.deepcopy(self.initial_sweep_states[index])
            self.sweep_features[index] = copy.deepcopy(self.initial_sweep_features[index])

        # updating sweep states and sweep features if this is an auto qc sweep
        elif new_state == "passed":
            self.sweep_states[index]['passed'] = True
            self.sweep_states[index]['reasons'].append("Manually passed")
            # deals with sweeps that break feature extraction
            if self.sweep_features[index]['passed'] is not None:
                self.sweep_features[index]['passed'] = True

        elif new_state == "failed":
            self.sweep_states[index]['passed'] = False
            self.sweep_states[index]['reasons'].append("Manually failed")
            # deals with sweeps that break feature extraction
            if self.sweep_features[index]['passed'] is not None:
                self.sweep_features[index]['passed'] = False

        # this shouldn't happen, but it's here just in case
        else:
            logging.warning(f"Unknown manual QC state: {new_state}"
                            f"for sweep number {index}")

        # notifies fx_data that the data has changed
        self.data_changed.emit(self.nwb_path,
                               self.stimulus_ontology,
                               self.sweep_features,
                               self.cell_features)


def extract_qc_features(data_set):
    """ Extracts QC information for the cell and the sweeps using ipfx.

    Parameters
    ----------
    data_set : EphysDataSet
        raw data used in qc feature extraction

    Returns
    -------
    cell_features : dict
        dictionary of qc info for the cell (overall experiment level info)
    cell_tags : list
        a list of qc tags for the cell (e.g. 'Blowout is not available')
    sweep_features : list[dict]
        a list of dictionaries containing qc info for each individual sweep

    """
    cell_features, cell_tags = cell_qc_features(data_set)
    sweep_features = sweep_qc_features(data_set)
    return cell_features, cell_tags, sweep_features


def run_qc(stimulus_ontology, cell_features, sweep_features, qc_criteria):
    """Adds qc status to sweep features and outputs a qc summary to the log.

    Parameters
    ----------
    stimulus_ontology : StimulusOntology
        stimulus ontology used for this data set
    cell_features : dict
        dictionary of qc info for the cell (overall experiment level info)
    sweep_features : list[dict]
        a list of dictionaries containing qc info for each individual sweep
    qc_criteria : dict
        a dictionary containing the criteria used for auto QC

    Returns
    -------
    cell_state : dict
        a dictionary of qc states for various cell level qc criteria
    cell_features : dict
        dictionary of qc info for the cell (overall experiment level info)
    sweep_states : List[dict]
        a list of dictionaries containing auto QC states
    post_qc_sweep_features : List[dict]
        similar to sweep_features input, but with rows removed for most sweeps
        that failed auto QC and new column containing the auto QC states

    """

    # making a copy of sweep_features so we don't lose the info from the first
    # round of auto QC
    post_qc_sweep_features = copy.deepcopy(sweep_features)
    cell_features = copy.deepcopy(cell_features)

    # tagged sweeps are dropped here so that qc_experiment() doesn't break due
    # to trying to handle sweeps that were terminated early
    drop_tagged_sweeps(post_qc_sweep_features)

    # extracts auto QC states for the cell and for sweeps passing the first
    # round of auto QC
    cell_state, sweep_states = qc_experiment(
        ontology=stimulus_ontology,
        cell_features=cell_features,
        sweep_features=post_qc_sweep_features,
        qc_criteria=qc_criteria
    )

    # outputs a summary of the auto QC results to the log
    qc_summary(
        sweep_features=post_qc_sweep_features,
        sweep_states=sweep_states, 
        cell_features=cell_features,
        cell_state=cell_state
    )

    return cell_state, cell_features, sweep_states, post_qc_sweep_features

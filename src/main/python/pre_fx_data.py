from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

from ipfx.ephys_data_set import EphysDataSet
from ipfx.qc_feature_extractor import cell_qc_features, sweep_qc_features
from ipfx.qc_feature_evaluator import qc_experiment
from ipfx.bin.run_qc import qc_summary
from ipfx.stimulus import StimulusOntology


from error_handling import exception_message


class PreFxData(QObject):

    new_data_set = pyqtSignal(name="new_pre_fx_data")
    # new_ontology = pyqtSignal(name="new_ontology")
    new_pre_fx_data = pyqtSignal(name="new_pre_fx_data")


    def __init__(self, *args, **kwargs):
        super(PreFxData, self).__init__(*args, **kwargs)

        self.data_set: Optional[EphysDataSet] = None


    def connect(self, settings):
        self.new_data_set.connect(settings.commit_nwb_path)


    def new_stimulus_ontology(self, ontology: StimulusOntology):
        if self.data_set is None:
            self.stimulus_ontology = ontology
            return

        try:
            self.recalculate(self.data_set, ontology)
            self.stimulus_ontology = ontology
            self.new_pre_fx_data.emit()
        except Exception as err:
            exception_message(
                "recalculation with new ontology failed", 
                "", 
                err
            )

    def recalculate(self, data_set, stimulus_ontology):
        cell_features, cell_tags = cell_qc_features(
            data_set,
            # manual_values=cell_qc_manual_values
        )
        sweep_features = sweep_qc_features(data_set)
            
        cell_state, sweep_states = qc_experiment(
            ontology=stimulus_ontology,
            cell_features=cell_features,
            sweep_features=sweep_features,
            # qc_criteria=qc_criteria
        )
        qc_summary(
            sweep_features=sweep_features, 
            sweep_states=sweep_states, 
            cell_features=cell_features, 
            cell_state=cell_state
        )

        return cell_features, cell_tags, sweep_features, cell_state, sweep_states


    def new_data(self, data_set):

        try:
            (
                self.cell_features, 
                self.cell_tags, 
                self.sweep_features, 
                self.cell_state, 
                self.sweep_states
            ) = self.recalculate(data_set, self.stimulus_ontology)

            self.new_data_set.emit()
            self.new_pre_fx_data.emit()

            self.data_set = data_set

        except Exception as err:
            exception_message(
                "extraction  or auto qc failed!",
                "",
                err
            )


        
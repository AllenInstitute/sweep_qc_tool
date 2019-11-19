import json
from pathlib import Path
from typing import Optional, Callable

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QFileDialog

from ipfx.stimulus import StimulusOntology
from ipfx.ephys_data_set import EphysDataSet
from ipfx.data_set_utils import create_data_set

from error_handling import exception_message


class Settings(QObject):
    """ Holds user settings and globally relevant information (e.g. the 
    locations of files).
    """

    new_stimulus_ontology: pyqtSignal = pyqtSignal(
        StimulusOntology, name="new_stimulus_ontology"
    )
    new_data_set: pyqtSignal = pyqtSignal(EphysDataSet, name="new_data_set")


    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)

        self.nwb_path: Optional[str] = None
        self._pending_nwb_path: Optional[str] = None

        self.stimulus_ontology: StimulusOntology = None


    def connect(self, pre_fx_data):
        self.new_data_set.connect(pre_fx_data.new_data)
        self.new_stimulus_ontology.connect(pre_fx_data.new_stimulus_ontology)


    def commit_nwb_path(self):
        self.nwb_path = self._pending_nwb_path
        self._pending_nwb_path = None


    def load_stimulus_ontology(self):
        self.stimulus_ontology = get_default_ontology()
        self.new_stimulus_ontology.emit(self.stimulus_ontology)


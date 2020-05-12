import pytest
import pytest_check as check

from PyQt5.QtWidgets import QWidget

import numpy as np

from pre_fx_data import PreFxData

from .test_sweep_plots import MockDataSet


MOCK_PRE_QC_FEATURES = [
    {'sweep_number': 0, 'stimulus_code': "foo", 'tags': []},
    {'sweep_number': 2, 'stimulus_code': "bar", 'tags': []},
    {'sweep_number': 3, 'stimulus_code': "foobar", 'tags': ["early termination"]},
    {'sweep_number': 5, 'stimulus_code': "fooRamp", 'tags': []}
]

MOCK_POST_QC_FEATURES = [
    {'sweep_number': 0, 'stimulus_code': "foo", 'tags': [], 'passed': True},
    {'sweep_number': 2, 'stimulus_code': "bar", 'tags': [], 'passed': True},
    {'sweep_number': 5, 'stimulus_code': "fooRamp", 'tags': [], 'passed': False}
]

MOCK_STATES = [
    {'sweep_number': 0, 'passed': True, 'reasons': []},
    {'sweep_number': 2, 'passed': True, 'reasons': []},
    {'sweep_number': 5, 'passed': False, 'reasons': ["baseline failure"]}
]


def test_populate_qc_info():
    pre_fx_data = PreFxData()
    pre_fx_data.data_set = MockDataSet()

    pre_fx_data.populate_qc_info(
        pre_qc_sweep_features=MOCK_PRE_QC_FEATURES,
        post_qc_sweep_features=MOCK_POST_QC_FEATURES,
        sweep_states=MOCK_STATES
    )

    num_sweeps = len(pre_fx_data.data_set.sweep_table)

    # initializing list of empty dicts with keys from post_qc_features
    expected_features = [
        dict.fromkeys(MOCK_POST_QC_FEATURES[0].keys())
        for _ in range(num_sweeps)
    ]

    # initializing sweep auto qc states
    expected_states = [{'passed': None, 'reasons': [], 'sweep_number': x}
                         for x in range(num_sweeps)]

    # populating sweep_features and sweep_states with
    # sweeps that made it through auto qc
    for index, row in enumerate(MOCK_POST_QC_FEATURES):
        expected_features[row['sweep_number']] = row
        expected_states[row['sweep_number']] = MOCK_STATES[index]

    # populating sweep_features and sweep_states with
    # rows that were dropped during run_qc() (usually terminated early)
    for row in MOCK_PRE_QC_FEATURES:
        if expected_features[row['sweep_number']]['passed'] is None:
            expected_features[row['sweep_number']].update(row)
            # Leaving sweep features 'passed' = None here to distinguish sweeps
            # weeded out after first round of auto-qc
            expected_states[row['sweep_number']]['passed'] = False

    # populating sweep_features and sweep_states with
    # rows that were not included in auto qc
    for index, row in pre_fx_data.data_set.sweep_table.iterrows():
        if expected_features[index]['sweep_number'] is None:
            expected_features[index].update(row)
            expected_features[index]['tags'] = []
            # sweep states with no auto QC have the "None" tag for auto-qc state
            expected_states[index]['reasons'] = ['No auto QC']

    assert expected_features == pre_fx_data.sweep_features == pre_fx_data.initial_sweep_features
    assert expected_states == pre_fx_data.sweep_states == pre_fx_data.initial_sweep_states
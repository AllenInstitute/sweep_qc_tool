import pytest

from PyQt5.QtWidgets import QMessageBox, QFileDialog

from pre_fx_controller import PreFxController


@pytest.fixture
def controller():
    return PreFxController()


class SingleArgTarget:

    def __init__(self, expected):
        self.num_calls = 0
        self.expected = expected
        self.obtained = None

    def __call__(self, obtained):
        self.num_calls += 1
        self.obtained = obtained
    
    def validate(self):
        if self.expected is None:
            assert self.obtained is None
        else:
            assert self.expected  == self.obtained


@pytest.fixture
def dialog_method_tester(qtbot, monkeypatch):
    def _dialog_method_tester(
        controller,
        target,
        signal_name,
        method_name,
        patches=None
    ):
        qtbot.addWidget(controller)

        if patches is None:
            patches = []

        for patch_spec in patches:
            monkeypatch.setattr(*patch_spec)

        getattr(controller, signal_name).connect(target)
        getattr(controller, method_name)()

        target.validate()

    return _dialog_method_tester


@pytest.mark.parametrize("proceed,path,expected", [
    [QMessageBox.No, "foo", None],
    [QMessageBox.Yes, "foo", "foo"],
    [QMessageBox.Yes, "", None]
])
def test_export_manual_states_to_json_dialog(
    dialog_method_tester, controller, 
    proceed, path, expected
):

    controller._fx_outdated = True
    controller.output_path = "default"

    dialog_method_tester(
        controller,
        SingleArgTarget(expected),
        "selected_manual_states_path",
        "export_manual_states_to_json_dialog",
        patches=[
            [QMessageBox, "question", lambda *args: proceed],
            [QFileDialog, "getSaveFileName", lambda *args: [path, "unused"]]
        ]
    )


@pytest.mark.parametrize("proceed,path,expected", [
    [QMessageBox.No, "foo", None],
    [QMessageBox.Yes, "foo", "foo"],
    [QMessageBox.Yes, "", None]
])
def test_load_stimulus_ontology_dialog(
    dialog_method_tester, controller, 
    proceed, path, expected
):

    controller._stimulus_ontology = 4

    dialog_method_tester(
        controller,
        SingleArgTarget(expected),
        "selected_stimulus_ontology_path",
        "load_stimulus_ontology_dialog",
        patches=[
            [QMessageBox, "question", lambda *args: proceed],
            [QFileDialog, "getOpenFileName", lambda *args: [path, "unused"]]
        ]
    )


@pytest.mark.parametrize("proceed,path,expected", [
    [QMessageBox.No, "foo", None],
    [QMessageBox.Yes, "foo", "foo"],
    [QMessageBox.Yes, "", None]
])
def test_load_qc_criteria_dialog(
    dialog_method_tester, controller, 
    proceed, path, expected
):

    controller._qc_criteria = 4

    dialog_method_tester(
        controller,
        SingleArgTarget(expected),
        "selected_qc_criteria_path",
        "load_qc_criteria_dialog",
        patches=[
            [QMessageBox, "question", lambda *args: proceed],
            [QFileDialog, "getOpenFileName", lambda *args: [path, "unused"]]
        ]
    )


@pytest.mark.parametrize("proceed,path,expected", [
    [QMessageBox.No, "foo", None],
    [QMessageBox.Yes, "foo", "foo"],
    [QMessageBox.Yes, "", None]
])
def test_load_data_set_dialog(
    dialog_method_tester, controller, 
    proceed, path, expected
):

    controller._has_data_set = True

    dialog_method_tester(
        controller,
        SingleArgTarget(expected),
        "selected_data_set_path",
        "load_data_set_dialog",
        patches=[
            [QMessageBox, "question", lambda *args: proceed],
            [QFileDialog, "getOpenFileName", lambda *args: [path, "unused"]]
        ]
    )

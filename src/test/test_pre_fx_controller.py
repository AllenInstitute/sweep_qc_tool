import pytest

from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog

from pre_fx_controller import PreFxController


@pytest.fixture
def controller():
    return PreFxController()


@pytest.mark.parametrize("proceed,path,expected", [
    [QMessageBox.No, "foo", None],
    [QMessageBox.Yes, "foo", "foo"],
    [QMessageBox.Yes, "", None]
])
def test_export_manual_states_to_json_dialog(controller, qtbot, monkeypatch, proceed, path, expected):

    num_calls = [0]

    def manual_path_target(obt_path):
        num_calls[0] += 1
        assert obt_path == expected

    qtbot.addWidget(controller)
    controller.selected_manual_states_path.connect(manual_path_target)
    controller._fx_outdated = True
    controller.output_path = "default"

    monkeypatch.setattr(QMessageBox, "question", lambda *args: proceed)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: [path, "unused"])
    controller.export_manual_states_to_json_dialog()
    
    if expected is None:
        assert num_calls[0] == 0
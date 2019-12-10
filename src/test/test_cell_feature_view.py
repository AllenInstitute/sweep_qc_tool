from cell_feature_view import CellFeatureView


def test_construction(qtbot):
    view = CellFeatureView("a", "b")
    qtbot.addWidget(view)

    assert view.layout().itemAt(0).widget().text() == "a"
    assert view.layout().itemAt(2).widget().text() == "b"

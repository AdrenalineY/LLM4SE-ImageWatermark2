import os
import sys

import pytest
from PyQt5.QtWidgets import QApplication


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
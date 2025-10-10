import math

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap

from app.ui.main_window import PreviewGraphicsView


@pytest.mark.parametrize("angle", [-135, -45, 0, 33, 87, 150])
def test_preview_rotation_matches_export(angle, qapp):
    view = PreviewGraphicsView()
    pixmap = QPixmap(800, 600)
    pixmap.fill(Qt.white)
    view.set_image(pixmap)

    font = QFont("Arial", 24)
    view.add_watermark_preview(
        text="Rotation",
        font=font,
        color=None,
        opacity=200,
        position=(400, 300),
        rotation=angle
    )

    item = view.watermark_item
    assert item is not None
    assert math.isclose(item.rotation(), -angle)

    center = view.get_watermark_position()
    assert center is not None
    assert abs(center[0] - 400) <= 1
    assert abs(center[1] - 300) <= 1

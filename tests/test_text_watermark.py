import pytest
from PIL import Image

from app.core.config_manager import WatermarkConfig
from app.core.image_processor import ImageProcessor


@pytest.fixture
def processor():
    return ImageProcessor()


def _capture_measurement(processor):
    captured = {}

    def fake_measure_text(text, font_family, font_size, bold, italic, stroke,
                           stroke_width, shadow, shadow_offset, rotation,
                           font_path, font_index):
        captured["font_path"] = font_path
        captured["font_index"] = font_index
        return 180, 64

    return captured, fake_measure_text


def _capture_render(processor):
    captured = {}

    def fake_add_text(image, text, position, opacity, font_size, font_family,
                      bold, italic, color, shadow, stroke, rotation,
                      shadow_offset, stroke_width, stroke_color, font_path,
                      font_index):
        captured["font_path"] = font_path
        captured["font_index"] = font_index
        return image

    return captured, fake_add_text


def test_apply_watermark_resolves_font_metadata(processor, monkeypatch):
    base_image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    config = WatermarkConfig()
    config.text = "Font metadata"
    config.font_family = "NonExistingFontFamily"
    config.font_bold = True
    config.font_italic = False
    config.font_path = ""
    config.font_index = 0

    resolved_path = "path/to/font.ttf"
    resolved_index = 2

    monkeypatch.setattr(
        processor,
        "resolve_font_face",
        lambda family, bold, italic: (resolved_path, resolved_index)
    )

    measure_capture, fake_measure = _capture_measurement(processor)
    monkeypatch.setattr(processor, "_measure_text", fake_measure)

    render_capture, fake_render = _capture_render(processor)
    monkeypatch.setattr(processor, "add_text_watermark", fake_render)

    processor.apply_watermark(base_image, config)

    assert measure_capture["font_path"] == resolved_path
    assert measure_capture["font_index"] == resolved_index
    assert render_capture["font_path"] == resolved_path
    assert render_capture["font_index"] == resolved_index
    assert config.font_path == resolved_path
    assert config.font_index == resolved_index


def test_rotated_text_not_clipped(processor):
    text = "Preview vs Export"
    font_family = "Arial"
    font_size = 48
    rotation = 37
    bold = True
    italic = False
    shadow = True
    stroke = True
    shadow_offset = (4, -3)
    stroke_width = 3

    resolved = processor.resolve_font_face(font_family, bold, italic)
    if resolved:
        font_path, font_index = resolved
    else:
        font_path, font_index = None, 0

    measured_width, measured_height = processor.measure_text(
        text,
        font_family,
        font_size,
        bold,
        italic,
        stroke,
        stroke_width,
        shadow,
        shadow_offset,
        rotation,
        font_path,
        font_index
    )

    assert measured_width > 0
    assert measured_height > 0

    base = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
    result = processor.add_text_watermark(
        base,
        text,
        position=(300, 300),
        opacity=255,
        font_size=font_size,
        font_family=font_family,
        bold=bold,
        italic=italic,
        color=(255, 255, 255),
        shadow=shadow,
        stroke=stroke,
        rotation=rotation,
        shadow_offset=shadow_offset,
        stroke_width=stroke_width,
        stroke_color=(0, 0, 0),
        font_path=font_path,
        font_index=font_index
    )

    alpha = result.split()[-1]
    bbox = alpha.getbbox()
    assert bbox is not None

    actual_width = bbox[2] - bbox[0]
    actual_height = bbox[3] - bbox[1]

    assert actual_width <= measured_width + 2
    assert actual_height <= measured_height + 2

    assert bbox[0] >= 0
    assert bbox[1] >= 0
    assert bbox[2] <= result.width
    assert bbox[3] <= result.height


def test_custom_position_uses_center(processor):
    base = Image.new("RGBA", (600, 480), (0, 0, 0, 0))
    config = WatermarkConfig()
    config.text = "Center check"
    config.font_family = "Arial"
    config.font_size = 36
    config.opacity = 200
    config.rotation_angle = 45
    config.text_shadow = True
    config.shadow_offset = (5, -3)
    config.text_stroke = True
    config.stroke_width = 2
    config.use_custom_position = True
    config.custom_position = (250, 220)

    result = processor.apply_watermark(base, config)
    alpha = result.split()[-1]
    bbox = alpha.getbbox()
    assert bbox is not None

    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2

    assert abs(center_x - config.custom_position[0]) <= 2
    assert abs(center_y - config.custom_position[1]) <= 2

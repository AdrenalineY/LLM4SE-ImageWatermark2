import os
import tempfile

import pytest
from PIL import Image
from PIL import ImageChops

from app.core.image_processor import ImageProcessor
from app.core.config_manager import WatermarkConfig


@pytest.fixture
def processor():
    return ImageProcessor()


@pytest.fixture
def base_image():
    return Image.new('RGB', (200, 100), color=(255, 0, 0))


def make_config(**overrides):
    config = WatermarkConfig()
    config.text = overrides.pop("text", "Test")
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def test_apply_watermark_resizes_by_percentage(processor, base_image):
    config = make_config(
        resize_enabled=True,
        resize_method="percentage",
        resize_percentage=50,
    )

    result = processor.apply_watermark(base_image, config)

    assert result.size == (100, 50)


def test_apply_watermark_resizes_by_width(processor, base_image):
    config = make_config(
        resize_enabled=True,
        resize_method="width",
        resize_width=80,
        keep_aspect_ratio=True,
    )

    result = processor.apply_watermark(base_image, config)

    assert result.size == (80, 40)


def test_apply_watermark_resizes_with_image_watermark(processor, base_image):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        watermark_path = tmp.name

    try:
        watermark_image = Image.new('RGBA', (20, 20), color=(0, 255, 0, 128))
        watermark_image.save(watermark_path)

        config = make_config(
            watermark_type="image",
            text="",  # 无需文本水印
            image_watermark_path=watermark_path,
            resize_enabled=True,
            resize_method="height",
            resize_height=50,
            keep_aspect_ratio=True,
            image_scale=1.0,
            image_opacity=255,
        )

        result = processor.apply_watermark(base_image, config)

        assert result.size == (100, 50)
    finally:
        if os.path.exists(watermark_path):
            os.remove(watermark_path)


def test_apply_watermark_with_rotation_shadow_stroke(processor, base_image):
    config = make_config(
        text="Rotate",
        rotation_angle=45,
        text_shadow=True,
        shadow_offset=(5, 5),
        text_stroke=True,
        stroke_width=2,
        stroke_color=(0, 0, 0),
        font_bold=True,
        font_italic=True,
        opacity=200,
    )

    result = processor.apply_watermark(base_image, config)

    assert result.size == base_image.size
    assert result.mode == 'RGBA'


def test_rotated_text_near_edge_not_truncated(processor, base_image):
    config = make_config(
        text="Edge",
        rotation_angle=75,
        text_shadow=True,
        shadow_offset=(3, 3),
        text_stroke=True,
        stroke_width=2,
        stroke_color=(0, 0, 0),
        opacity=220,
        use_custom_position=True,
        custom_position=(15, 15)
    )

    result = processor.apply_watermark(base_image, config)

    diff = ImageChops.difference(result.convert('RGB'), base_image.convert('RGB'))
    bbox = diff.getbbox()

    assert bbox is not None
    left, top, right, bottom = bbox
    assert right - left > 10
    assert bottom - top > 10


def test_image_watermark_rotation_matches_preview_direction(processor, base_image):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        watermark_path = tmp.name

    try:
        watermark = Image.new('RGBA', (8, 4), color=(0, 0, 0, 0))
        for x in range(4):
            watermark.putpixel((x, 1), (0, 255, 0, 255))
        watermark.putpixel((3, 0), (0, 255, 0, 255))
        watermark.putpixel((3, 2), (0, 255, 0, 255))
        watermark.save(watermark_path)

        config = make_config(
            text="",
            watermark_type="image",
            image_watermark_path=watermark_path,
            image_scale=1.0,
            image_opacity=255,
            rotation_angle=45,
            use_custom_position=True,
            custom_position=(30, 20)
        )

        result = processor.apply_watermark(base_image, config)

        base_rgba = base_image.convert('RGBA')
        watermark_rgba = Image.open(watermark_path).convert('RGBA')
        rotated = watermark_rgba.rotate(config.rotation_angle, resample=Image.BICUBIC, expand=True)
        overlay = Image.new('RGBA', base_rgba.size, (0, 0, 0, 0))
        overlay.alpha_composite(rotated, dest=config.custom_position)
        expected = Image.alpha_composite(base_rgba, overlay)

        diff = ImageChops.difference(result, expected)
        assert diff.getbbox() is None
    finally:
        if os.path.exists(watermark_path):
            os.remove(watermark_path)
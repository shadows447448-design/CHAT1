from pathlib import Path

import pytest

from image_clarity_desktop import (
    EnhanceSettings,
    duck_x_for_progress,
    enhance_image,
    is_supported_image,
    output_path_for,
    process_many,
)


def test_enhance_image_upscales_and_preserves_mode():
    pytest.importorskip("PIL")
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (80, 32), "white")
    draw = ImageDraw.Draw(image)
    draw.text((5, 8), "TEXT 123", fill="black")

    enhanced = enhance_image(image, EnhanceSettings(scale=2.0, sharpness=1.4, text_protection=0.8))

    assert enhanced.size == (160, 64)
    assert enhanced.mode == "RGB"


def test_output_path_for_avoids_overwriting_existing_files(tmp_path):
    source = tmp_path / "sample.png"
    source.write_bytes(b"placeholder")
    first = output_path_for(source, tmp_path)
    first.write_bytes(b"existing")

    second = output_path_for(source, tmp_path)

    assert first.name == "sample_清晰放大.png"
    assert second.name == "sample_清晰放大_2.png"


def test_process_many_handles_multiple_uploads(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    sources = []
    for index in range(2):
        path = tmp_path / f"input_{index}.png"
        Image.new("RGB", (12, 10), "white").save(path)
        sources.append(path)
    output_dir = tmp_path / "out"
    progress = []

    results = process_many(
        sources,
        output_dir,
        EnhanceSettings(scale=1.5, sharpness=1.2, denoise=False),
        lambda index, total, target: progress.append((index, total, Path(target).name)),
    )

    assert len(results) == 2
    assert all(path.exists() for path in results)
    assert progress == [(1, 2, "input_0_清晰放大.png"), (2, 2, "input_1_清晰放大.png")]


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("a.JPG", True), ("b.webp", True), ("c.txt", False)],
)
def test_is_supported_image(filename, expected):
    assert is_supported_image(Path(filename)) is expected


def test_duck_progress_position_is_clamped_and_moves_forward():
    assert duck_x_for_progress(-10, 300) == duck_x_for_progress(0, 300)
    assert duck_x_for_progress(100, 300) == duck_x_for_progress(150, 300)
    assert duck_x_for_progress(50, 300) > duck_x_for_progress(0, 300)
    assert duck_x_for_progress(100, 300) > duck_x_for_progress(50, 300)

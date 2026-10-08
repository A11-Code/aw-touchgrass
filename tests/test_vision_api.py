from datetime import datetime, timedelta
from PIL import Image

import vision_api


def _write_image(path, captured_at=None):
    image = Image.new("RGB", (8, 8), "green")
    if captured_at:
        exif = image.getexif()
        exif[36867] = captured_at.strftime("%Y:%m:%d %H:%M:%S")
        image.save(path, exif=exif)
    else:
        image.save(path)


def test_image_created_today_is_accepted(tmp_path):
    path = tmp_path / "today.jpg"
    _write_image(path, datetime.now())

    result = vision_api.verify_image(path)

    assert result.accepted
    assert path.exists()


def test_image_from_yesterday_is_rejected(tmp_path):
    path = tmp_path / "yesterday.jpg"
    _write_image(path, datetime.now() - timedelta(days=1))

    result = vision_api.verify_image(path)

    assert not result.accepted
    assert "not today" in result.reason
    assert path.exists()


def test_metadata_free_file_created_today_is_suspicious(tmp_path):
    path = tmp_path / "fresh_no_exif.png"
    _write_image(path)

    result = vision_api.verify_image(path)

    assert result.accepted
    assert result.suspicious
    assert path.exists()

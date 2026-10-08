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


def test_old_metadata_is_rejected_and_file_is_preserved(tmp_path, monkeypatch):
    path = tmp_path / "old.jpg"
    _write_image(path, datetime.now() - timedelta(hours=4))
    monkeypatch.setattr(vision_api, "_vision_yes", lambda _path: True)

    result = vision_api.verify_image(path)

    assert not result.accepted
    assert path.exists()


def test_metadata_free_positive_result_is_suspicious(tmp_path, monkeypatch):
    path = tmp_path / "fresh.png"
    _write_image(path)
    monkeypatch.setattr(vision_api, "_vision_yes", lambda _path: True)

    result = vision_api.verify_image(path)

    assert result.accepted
    assert result.suspicious
    assert path.exists()


def test_openrouter_vision_yes_response(tmp_path, monkeypatch):
    path = tmp_path / "grass.jpg"
    _write_image(path)

    class DummyResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "YES"
                        }
                    }
                ]
            }

        def raise_for_status(self):
            pass

    monkeypatch.setattr(vision_api, "_get_openrouter_key", lambda: "mock_openrouter_key")
    monkeypatch.setattr("requests.post", lambda *args, **kwargs: DummyResponse())

    assert vision_api._vision_yes(path) is True


def test_openrouter_vision_no_response(tmp_path, monkeypatch):
    path = tmp_path / "screen.png"
    _write_image(path)

    class DummyResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "NO"
                        }
                    }
                ]
            }

        def raise_for_status(self):
            pass

    monkeypatch.setattr(vision_api, "_get_openrouter_key", lambda: "mock_openrouter_key")
    monkeypatch.setattr("requests.post", lambda *args, **kwargs: DummyResponse())

    assert vision_api._vision_yes(path) is False

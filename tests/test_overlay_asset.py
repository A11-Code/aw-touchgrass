import unittest
from pathlib import Path

from PIL import Image


class OverlayAssetTests(unittest.TestCase):
    def test_mascot_png_exists_and_can_be_resized(self):
        asset = Path(__file__).resolve().parents[1] / "mascot.png"
        self.assertTrue(asset.is_file())
        with Image.open(asset) as image:
            resized = image.convert("RGBA").resize((100, 100), Image.Resampling.LANCZOS)
            self.assertEqual(resized.size, (100, 100))


if __name__ == "__main__":
    unittest.main()

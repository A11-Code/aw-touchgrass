"""Tests for proof storage archive and retention cleanup policy."""

from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

from vision_api import cleanup_old_proofs, save_proof_image


class ProofRetentionTestCase(unittest.TestCase):
    def test_save_and_cleanup_proofs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            proof_file = test_dir / "test_grass.jpg"
            proof_file.write_bytes(b"dummy image content")

            saved_path = save_proof_image(proof_file, proofs_dir=test_dir / "proofs")
            self.assertTrue(saved_path.exists())
            self.assertTrue(saved_path.name.startswith("proof_"))

            # Test cleanup retention with expired timestamp modification
            expired_file = test_dir / "proofs" / "proof_20200101_000000_old.jpg"
            expired_file.write_bytes(b"old content")
            old_mtime = (datetime.now() - timedelta(days=40)).timestamp()
            import os

            os.utime(expired_file, (old_mtime, old_mtime))

            removed_count = cleanup_old_proofs(retention_days=30, proofs_dir=test_dir / "proofs")
            self.assertEqual(removed_count, 1)
            self.assertFalse(expired_file.exists())
            self.assertTrue(saved_path.exists())


if __name__ == "__main__":
    unittest.main()

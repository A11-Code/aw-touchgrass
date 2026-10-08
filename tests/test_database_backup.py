"""Tests for database backup functionality."""

from pathlib import Path
import tempfile
import unittest

from database import backup_database, initialize_database, insert_log, get_recent_logs


class DatabaseBackupTestCase(unittest.TestCase):
    def test_database_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_ratiobot.sqlite3"
            backup_path = Path(temp_dir) / "test_ratiobot.sqlite3.bak"

            initialize_database(db_path)
            insert_log("Chrome", 120.0, 1, database_path=db_path)

            created_backup = backup_database(database_path=db_path, backup_path=backup_path)
            self.assertTrue(created_backup.exists())

            # Verify backup contains the same data
            logs = get_recent_logs(database_path=backup_path)
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["trigger_app"], "Chrome")


if __name__ == "__main__":
    unittest.main()

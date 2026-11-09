import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

from cloud_backend.tasks.garbage_collector import cleanup_orphaned_files


def test_cleanup_uses_utc_for_orphan_file_age(tmp_path: Path) -> None:
    orphan = tmp_path / "upload_42.tmp"
    orphan.write_bytes(b"orphan")
    old_time = (datetime.now(UTC) - timedelta(hours=2)).timestamp()
    orphan.touch()
    os.utime(orphan, (old_time, old_time))

    db = Mock()
    db.scalar.return_value = None
    db.scalars.return_value.all.return_value = []

    assert cleanup_orphaned_files(str(tmp_path), db) == 1
    assert not orphan.exists()

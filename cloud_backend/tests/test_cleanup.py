from datetime import UTC, datetime
from unittest.mock import Mock

from cloud_backend.tasks.cleanup import cleanup_inactive_sessions


def test_cleanup_inactive_sessions_revokes_tokens_and_commits() -> None:
    db = Mock()
    db.execute.return_value.scalars.return_value.all.return_value = [4, 8]
    now = datetime(2026, 1, 1, tzinfo=UTC)

    assert cleanup_inactive_sessions(db, now) == 2
    assert db.execute.call_count == 2
    db.commit.assert_called_once_with()

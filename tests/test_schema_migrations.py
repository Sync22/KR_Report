import sqlite3

import pytest

from stock_monitor.db.repository import StockMonitorRepository


def test_schema_migration_dry_run_rejects_a_newer_database(tmp_path) -> None:
    db_path = tmp_path / "future.db"
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA user_version = 999")
    connection.close()

    repository = StockMonitorRepository(db_path)
    with pytest.raises(RuntimeError, match="newer than supported version"):
        repository.migrate_schema(dry_run=True)

    with repository.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 999

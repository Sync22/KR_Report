from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path


SQLITE_SIDECAR = re.compile(r"\.(?:db|sqlite|sqlite3)-(?:wal|shm|journal)$", re.IGNORECASE)


def _configured_database_path(project_root: Path) -> Path:
    project_root = project_root.resolve(strict=True)
    sys.path.insert(0, str(project_root / "src"))
    from stock_monitor.config import RuntimeConfig

    database_path = RuntimeConfig.from_env(root_dir=project_root).db_path
    return database_path.resolve() if database_path.is_absolute() else (project_root / database_path).resolve()


def _connect_read_only(database_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{database_path.resolve(strict=True).as_uri()}?mode=ro", uri=True, timeout=30.0)


def _verify_database(database_path: Path) -> None:
    with closing(_connect_read_only(database_path)) as connection:
        connection.execute("PRAGMA query_only = ON")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity_check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("SQLite foreign_key_check failed")


def _snapshot_database(source_path: Path, snapshot_path: Path) -> None:
    source_path = source_path.resolve(strict=True)
    snapshot_path = snapshot_path.resolve()
    if source_path == snapshot_path:
        raise ValueError("SQLite snapshot destination must differ from its source")
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    source = _connect_read_only(source_path)
    snapshot = sqlite3.connect(snapshot_path, timeout=30.0)
    try:
        source.execute("PRAGMA query_only = ON")
        source.backup(snapshot, pages=256, sleep=0.01)
        snapshot.execute("PRAGMA journal_mode = DELETE")
        snapshot.commit()
    finally:
        snapshot.close()
        source.close()

    _verify_database(snapshot_path)


def _verify_archive(archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        names = [entry.filename.replace("\\", "/") for entry in archive.infolist()]
        if any(SQLITE_SIDECAR.search(name.rsplit("/", 1)[-1]) for name in names):
            raise ValueError("Archive contains live SQLite sidecar files")
        databases = [
            entry
            for entry in archive.infolist()
            if entry.filename.replace("\\", "/") == "data/stock_monitor.db"
            or entry.filename.replace("\\", "/").endswith("/data/stock_monitor.db")
        ]
        if len(databases) != 1:
            raise ValueError("Archive must contain exactly one data/stock_monitor.db")
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "stock_monitor.db"
            with archive.open(databases[0]) as source, database_path.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            _verify_database(database_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or validate a migration archive SQLite snapshot.")
    commands = parser.add_subparsers(dest="command", required=True)
    resolve = commands.add_parser("resolve-db-path")
    resolve.add_argument("project_root", type=Path)
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("source", type=Path)
    snapshot.add_argument("destination", type=Path)
    verify = commands.add_parser("verify-archive")
    verify.add_argument("archive", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "resolve-db-path":
            print(_configured_database_path(args.project_root))
        elif args.command == "snapshot":
            _snapshot_database(args.source, args.destination)
        else:
            _verify_archive(args.archive)
    except (OSError, sqlite3.Error, ValueError, zipfile.BadZipFile) as error:
        print(f"Migration archive SQLite check failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

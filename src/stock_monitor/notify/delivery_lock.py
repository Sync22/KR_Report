from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from stock_monitor.file_lock import exclusive_file_lock


@contextmanager
def delivery_lock(db_path: Path) -> Iterator[None]:
    lock_path = db_path.with_name(f"{db_path.name}.delivery.lock")
    with exclusive_file_lock(lock_path):
        yield

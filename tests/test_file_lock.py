from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from threading import Event, Thread

from stock_monitor.file_lock import FILE_LOCK_MARKER, exclusive_file_lock


def test_created_file_lock_preserves_content_written_by_the_first_owner(tmp_path: Path) -> None:
    lock_path = tmp_path / "shared.lock"
    child_code = "\n".join((
        "import sys",
        "sys.path.insert(0, sys.argv[1])",
        "sys.path.insert(0, sys.argv[3])",
        "from pathlib import Path",
        "from stock_monitor.file_lock import exclusive_file_lock",
        "lock_path = Path(sys.argv[2])",
        "original_open = Path.open",
        "def delayed_open(path, mode='r', *args, **kwargs):",
        "    handle = original_open(path, mode, *args, **kwargs)",
        "    if path == lock_path and mode == 'x+b':",
        "        print('created', flush=True)",
        "        sys.stdin.readline()",
        "    return handle",
        "Path.open = delayed_open",
        "with exclusive_file_lock(lock_path) as handle:",
        "    handle.seek(0)",
        "    print(handle.read().decode(), flush=True)",
    ))
    process = subprocess.Popen(
        [sys._base_executable, "-c", child_code, str(Path(__file__).resolve().parents[1] / "src"), str(lock_path), str(Path(sys.prefix) / "Lib" / "site-packages")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None

    def read_line() -> str:
        line = []
        done = Event()
        reader = Thread(target=lambda: (line.append(process.stdout.readline().strip()), done.set()))
        reader.start()
        assert done.wait(5)
        reader.join(timeout=5)
        return line[0]

    try:
        assert read_line() == "created"
        with exclusive_file_lock(lock_path) as handle:
            handle.seek(0)
            handle.truncate()
            handle.write(b"first-owner-payload")
            handle.flush()
        assert process.stdin is not None
        process.stdin.write("\n")
        process.stdin.flush()
        assert read_line() == "first-owner-payload"
        assert process.wait(timeout=5) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_empty_existing_file_lock_is_initialized_after_locking(tmp_path: Path) -> None:
    lock_path = tmp_path / "empty.lock"
    lock_path.write_bytes(b"")
    with exclusive_file_lock(lock_path) as handle:
        handle.seek(0)
        assert handle.read() == FILE_LOCK_MARKER
    assert lock_path.read_bytes() == FILE_LOCK_MARKER


def test_existing_empty_legacy_lock_is_not_initialized(tmp_path: Path) -> None:
    lock_path = tmp_path / "legacy.lock"
    lock_path.write_bytes(b"")
    with exclusive_file_lock(lock_path, initialize_existing=False) as handle:
        assert handle.read() == b""
    assert lock_path.read_bytes() == b""

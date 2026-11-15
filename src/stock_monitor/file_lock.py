from __future__ import annotations

import errno
import os
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator


FILE_LOCK_MARKER = b"STOCK_MONITOR_KERNEL_FILE_LOCK_V1\n"
_RETRY_LOCK_ERRNOS = {errno.EACCES, errno.EDEADLK, getattr(errno, "EDEADLOCK", errno.EDEADLK)}
_BUSY_LOCK_ERRNOS = _RETRY_LOCK_ERRNOS | {errno.EAGAIN, errno.EWOULDBLOCK}


@contextmanager
def exclusive_file_lock(file_path: Path, *, blocking: bool = True) -> Iterator[BinaryIO]:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            handle = file_path.open("x+b")
        except FileExistsError:
            try:
                handle = file_path.open("r+b")
            except FileNotFoundError:
                continue
        break

    locked = False
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
            while True:
                try:
                    msvcrt.locking(handle.fileno(), mode, 1)
                    locked = True
                    break
                except OSError as error:
                    if not blocking and error.errno in _BUSY_LOCK_ERRNOS:
                        raise BlockingIOError(errno.EWOULDBLOCK, "file lock is held", str(file_path)) from error
                    if blocking and error.errno in _RETRY_LOCK_ERRNOS:
                        continue
                    raise
        else:
            import fcntl

            mode = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
            try:
                fcntl.flock(handle.fileno(), mode)
                locked = True
            except OSError as error:
                if not blocking and error.errno in _BUSY_LOCK_ERRNOS:
                    raise BlockingIOError(errno.EWOULDBLOCK, "file lock is held", str(file_path)) from error
                raise

        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(FILE_LOCK_MARKER)
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        yield handle
    finally:
        try:
            if locked:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

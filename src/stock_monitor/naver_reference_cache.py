from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future
from threading import Lock
from time import monotonic
from typing import Callable


class NaverReferenceCache:
    def __init__(self, *, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._lock = Lock()
        self._cache: OrderedDict[str, tuple[float, dict[str, object]]] = OrderedDict()
        self._inflight: dict[str, Future[tuple[dict[str, object], bool]]] = {}

    def get_or_build(
        self,
        key: str,
        build: Callable[[], dict[str, object]],
        cacheable: Callable[[dict[str, object]], bool],
    ) -> tuple[dict[str, object], str]:
        now = self._clock()
        with self._lock:
            cached = self._cache.get(key)
            if cached and now - cached[0] <= 30:
                self._cache.move_to_end(key)
                return cached[1], "hit"
            if cached:
                del self._cache[key]
            flight = self._inflight.get(key)
            owner = flight is None
            if flight is None:
                flight = Future()
                self._inflight[key] = flight

        if not owner:
            payload, stored = flight.result()
            return payload, "hit" if stored else "shared"

        try:
            payload = build()
            stored = cacheable(payload)
            if stored:
                with self._lock:
                    self._cache[key] = (self._clock(), payload)
                    self._cache.move_to_end(key)
                    while len(self._cache) > 256:
                        self._cache.popitem(last=False)
            flight.set_result((payload, stored))
            return payload, "miss" if stored else "uncached"
        except BaseException as error:
            flight.set_exception(error)
            raise
        finally:
            with self._lock:
                if self._inflight.get(key) is flight:
                    del self._inflight[key]

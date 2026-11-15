from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import Future as BaseFuture
from threading import Event

import stock_monitor.naver_reference_cache as naver_reference_cache
from stock_monitor.naver_reference_cache import NaverReferenceCache


def _cacheable(payload: dict[str, object]) -> bool:
    return not payload["errors"]


def test_naver_reference_cache_reuses_provenance_until_ttl_expiry() -> None:
    now = 0.0
    calls = 0
    cache = NaverReferenceCache(clock=lambda: now)

    def build():
        nonlocal calls
        calls += 1
        return {"checked_at": f"check-{calls}", "errors": []}

    first, first_status = cache.get_or_build("2026-11-16:005930,000660", build, _cacheable)
    cached, cache_status = cache.get_or_build("2026-11-16:005930,000660", build, _cacheable)

    assert first_status == "miss"
    assert cache_status == "hit"
    assert cached == first
    assert calls == 1

    now = 30.001
    expired, expired_status = cache.get_or_build("2026-11-16:005930,000660", build, _cacheable)
    assert expired_status == "miss"
    assert expired["checked_at"] == "check-2"
    assert calls == 2


def test_naver_reference_cache_does_not_store_errors() -> None:
    cache = NaverReferenceCache(clock=lambda: 0)
    calls = 0

    def build():
        nonlocal calls
        calls += 1
        return {"errors": ["005930"]}

    for _ in range(2):
        payload, status = cache.get_or_build("2026-11-16:005930", build, _cacheable)
        assert payload["errors"] == ["005930"]
        assert status == "uncached"

    assert calls == 2


def test_naver_reference_cache_shares_same_key_inflight_success(monkeypatch) -> None:
    waiter_joined = Event()

    class TrackedFuture(BaseFuture):
        def result(self, *args, **kwargs):
            waiter_joined.set()
            return super().result(*args, **kwargs)

    monkeypatch.setattr(naver_reference_cache, "Future", TrackedFuture)
    cache = NaverReferenceCache(clock=lambda: 0)
    started = Event()
    release = Event()
    calls = 0

    def build():
        nonlocal calls
        calls += 1
        started.set()
        assert release.wait(2)
        return {"checked_at": "original", "errors": []}

    def get():
        return cache.get_or_build("2026-11-16:005930", build, _cacheable)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(get)
        assert started.wait(2)
        second = executor.submit(get)
        assert waiter_joined.wait(2)
        release.set()
        first_value = first.result(timeout=2)
        second_value = second.result(timeout=2)

    assert calls == 1
    assert first_value[0] == second_value[0] == {"checked_at": "original", "errors": []}


def test_naver_reference_cache_shares_inflight_failure_then_retries(monkeypatch) -> None:
    waiter_joined = Event()

    class TrackedFuture(BaseFuture):
        def result(self, *args, **kwargs):
            waiter_joined.set()
            return super().result(*args, **kwargs)

    monkeypatch.setattr(naver_reference_cache, "Future", TrackedFuture)
    cache = NaverReferenceCache(clock=lambda: 0)
    started = Event()
    release = Event()
    fail = True
    calls = 0

    def build():
        nonlocal calls
        calls += 1
        if fail:
            started.set()
            assert release.wait(2)
            return {"errors": ["005930"]}
        return {"checked_at": "retry", "errors": []}

    def get():
        return cache.get_or_build("2026-11-16:005930", build, _cacheable)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(get)
        assert started.wait(2)
        second = executor.submit(get)
        assert waiter_joined.wait(2)
        release.set()
        first_value = first.result(timeout=2)
        second_value = second.result(timeout=2)

    assert calls == 1
    assert first_value[0] == second_value[0] == {"errors": ["005930"]}
    assert {first_value[1], second_value[1]} == {"uncached", "shared"}

    fail = False
    retry, status = cache.get_or_build("2026-11-16:005930", build, _cacheable)
    assert retry["checked_at"] == "retry"
    assert status == "miss"
    assert calls == 2


def test_naver_reference_cache_evicts_oldest_after_256_keys() -> None:
    cache = NaverReferenceCache(clock=lambda: 0)
    calls: list[str] = []

    def build(key: str):
        def make_payload():
            calls.append(key)
            return {"key": key, "errors": []}
        return make_payload

    for index in range(257):
        key = f"2026-11-16:0059{index:02d}"
        cache.get_or_build(key, build(key), _cacheable)

    cache.get_or_build("2026-11-16:005900", build("2026-11-16:005900"), _cacheable)

    assert len(calls) == 258
    assert calls[-1] == "2026-11-16:005900"

import threading

_report_cache: dict[tuple, dict] = {}
_availability_cache: dict[tuple, dict] = {}
_lock = threading.Lock()


def get_report(org_id: int, frm: str, to: str):
    with _lock:
        return _report_cache.get((org_id, frm, to))


def set_report(org_id: int, frm: str, to: str, value: dict) -> None:
    with _lock:
        _report_cache[(org_id, frm, to)] = value


def invalidate_report(org_id: int) -> None:
    with _lock:
        for key in [k for k in _report_cache if k[0] == org_id]:
            _report_cache.pop(key, None)


def get_availability(room_id: int, date: str):
    with _lock:
        return _availability_cache.get((room_id, date))


def set_availability(room_id: int, date: str, value: dict) -> None:
    with _lock:
        _availability_cache[(room_id, date)] = value


def invalidate_availability(room_id: int, date: str) -> None:
    with _lock:
        _availability_cache.pop((room_id, date), None)

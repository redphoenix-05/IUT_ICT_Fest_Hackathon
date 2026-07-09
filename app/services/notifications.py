"""Side effects that accompany booking lifecycle events.

Each booking change sends a (simulated) notification email and appends an
audit-log entry. Both resources are guarded by locks so their output stays
consistent when many requests are processed at once.
"""
import concurrent.futures
import threading
import time

_email_lock = threading.Lock()
_audit_lock = threading.Lock()

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


class EagerRefund:
    def __init__(self, refund):
        self.id = refund.id
        self.booking_id = refund.booking_id
        self.amount_cents = refund.amount_cents
        self.status = refund.status
        self.processed_at = refund.processed_at


class EagerBooking:
    def __init__(self, booking):
        self.id = booking.id
        self.room_id = booking.room_id
        self.user_id = booking.user_id
        self.start_time = booking.start_time
        self.end_time = booking.end_time
        self.status = booking.status
        self.reference_code = booking.reference_code
        self.price_cents = booking.price_cents
        self.created_at = booking.created_at
        self.refunds = [EagerRefund(r) for r in (getattr(booking, "refunds", None) or [])]


def _send_email(kind: str, booking) -> None:
    # Simulated SMTP round-trip.
    time.sleep(0.12)


def _write_audit(kind: str, booking) -> None:
    # Simulated audit-log formatting/flush.
    time.sleep(0.1)


def _notify_created_sync(booking) -> None:
    with _email_lock:
        _send_email("created", booking)
    with _audit_lock:
        _write_audit("created", booking)


def notify_created(booking) -> None:
    eager_booking = EagerBooking(booking)
    _executor.submit(_notify_created_sync, eager_booking)


def _notify_cancelled_sync(booking) -> None:
    with _email_lock:
        _send_email("cancelled", booking)
    with _audit_lock:
        _write_audit("cancelled", booking)


def notify_cancelled(booking) -> None:
    eager_booking = EagerBooking(booking)
    _executor.submit(_notify_cancelled_sync, eager_booking)

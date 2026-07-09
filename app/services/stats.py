"""Live per-room booking statistics.

Confirmed-booking counts and revenue are computed directly from the database
so they are always consistent with the bookings themselves.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Booking


def record_create(room_id: int, price_cents: int) -> None:
    pass


def record_cancel(room_id: int, price_cents: int) -> None:
    pass


def get(room_id: int, db: Session) -> dict:
    result = (
        db.query(
            func.count(Booking.id),
            func.coalesce(func.sum(Booking.price_cents), 0),
        )
        .filter(Booking.room_id == room_id, Booking.status == "confirmed")
        .first()
    )
    return {"count": result[0], "revenue": result[1]}


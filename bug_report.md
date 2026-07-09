# Bug Report

## Bug 1 — Timezone Conversion Strips Offset Without Converting
- **File/Line:** `app/timeutils.py`, line 13
- **Difficulty:** Easy
- **Bug:** `parse_input_datetime()` did `dt.replace(tzinfo=None)` which strips the timezone offset without actually converting the datetime to UTC. An input like `2026-07-10T12:00:00+06:00` would be stored as `2026-07-10T12:00:00` instead of the correct `2026-07-10T06:00:00`.
- **Fix:** Changed to `dt.astimezone(timezone.utc).replace(tzinfo=None)` which first converts the datetime to UTC, then strips the timezone info for storage.

## Bug 2 — Booking Allows Past Start Times (5-Minute Grace Window)
- **File/Line:** `app/routers/bookings.py`, line 86
- **Difficulty:** Easy
- **Bug:** The condition `start <= now - timedelta(seconds=300)` allowed bookings starting up to 5 minutes in the past. The spec states: "start_time must be strictly in the future at request time — no grace window."
- **Fix:** Changed to `start <= now` so bookings must start strictly in the future.

## Bug 3 — Missing end_time and Minimum Duration Validation
- **File/Line:** `app/routers/bookings.py`, lines 89-94
- **Difficulty:** Easy
- **Bug:** No check for `end_time <= start_time`, and no minimum duration check (< 1 hour). The spec requires "end_time must be strictly after start_time" and "minimum 1, maximum 8" hours.
- **Fix:** Added explicit `end <= start` check returning 400, and changed the duration validation from `duration_hours > MAX_DURATION_HOURS` to `duration_hours < MIN_DURATION_HOURS or duration_hours > MAX_DURATION_HOURS`.

## Bug 4 — Refund: 0% Tier Returns 50% Instead
- **File/Line:** `app/routers/bookings.py`, line 206
- **Difficulty:** Easy
- **Bug:** The `else` branch (notice < 24 hours) set `refund_percent = 50` instead of the correct `0`. Spec says: "notice < 24 hours → 0% refund."
- **Fix:** Changed `refund_percent = 50` to `refund_percent = 0`.

## Bug 5 — Refund: ≥48h Boundary Uses Strict > Instead of ≥
- **File/Line:** `app/routers/bookings.py`, line 201
- **Difficulty:** Easy
- **Bug:** `notice_hours > 48` used integer-truncated hours with strict `>`. Spec says "notice ≥ 48 hours → 100% refund." A booking with exactly 48h notice would incorrectly get 50% instead of 100%. Also used `int(notice.total_seconds() // 3600)` which truncates fractional hours.
- **Fix:** Changed to `notice >= timedelta(hours=48)` using the timedelta directly for accurate comparison.

## Bug 6 — Refund: Lossy Float Math in RefundLog Amount
- **File/Line:** `app/services/refunds.py`, lines 15-17
- **Difficulty:** Easy/Medium
- **Bug:** Converted cents → dollars (float division) → refund dollars → back to cents. This double float conversion loses precision. For example, `price_cents=1001, percent=50` would give `int(5.005 * 100) = 500` instead of 501.
- **Fix:** Replaced with `Decimal(price_cents) * Decimal(percent) / Decimal(100)` with `ROUND_HALF_UP` quantization.

## Bug 7 — Refund: Python's round() Uses Banker's Rounding
- **File/Line:** `app/routers/bookings.py`, line 208
- **Difficulty:** Easy
- **Bug:** `round(booking.price_cents * (refund_percent / 100.0))` uses Python's built-in `round()` which does banker's rounding (round-half-to-even). Spec says "half-cents rounding up." For example, `round(50.5)` gives `50`, not `51`.
- **Fix:** Replaced with `Decimal` math and `ROUND_HALF_UP` rounding mode.

## Bug 8 — Pagination: Sort Order Descending Instead of Ascending
- **File/Line:** `app/routers/bookings.py`, line 137
- **Difficulty:** Easy
- **Bug:** `Booking.start_time.desc()` sorts bookings in descending order. Spec says: "sorted ascending by start_time (ties by ascending id)."
- **Fix:** Changed to `Booking.start_time.asc()`.

## Bug 9 — Pagination: Offset Off-by-One
- **File/Line:** `app/routers/bookings.py`, line 138
- **Difficulty:** Easy
- **Bug:** `.offset(page * limit)` skips `page * limit` rows. For `page=1, limit=10`, this skips the first 10 items, returning page 2's data instead. Correct formula is `(page - 1) * limit`.
- **Fix:** Changed to `.offset((page - 1) * limit)`.

## Bug 10 — Pagination: Hardcoded limit(10) Ignores User's Limit Parameter
- **File/Line:** `app/routers/bookings.py`, line 139
- **Difficulty:** Easy
- **Bug:** `.limit(10)` is hardcoded regardless of the user's `limit` query parameter. If a user requests `limit=2`, they still get 10 results.
- **Fix:** Changed to `.limit(limit)`.

## Bug 11 — GET /bookings/{id}: Member Can See Any Org Booking
- **File/Line:** `app/routers/bookings.py`, lines 150-175
- **Difficulty:** Medium
- **Bug:** Missing visibility check for members. The endpoint only filters by `org_id` but doesn't check `user_id` for non-admin users. Spec says: "Members may read only their own bookings (another member's booking id → 404 BOOKING_NOT_FOUND)."
- **Fix:** Added `if user.role != "admin" and booking.user_id != user.id: raise AppError(404, ...)`.

## Bug 12 — GET /bookings/{id}: start_time Overwritten with created_at
- **File/Line:** `app/routers/bookings.py`, line 166
- **Difficulty:** Easy
- **Bug:** `response["start_time"] = iso_utc(booking.created_at)` overwrites the correct `start_time` (already set by `serialize_booking`) with the booking's `created_at` timestamp. This is a data corruption bug.
- **Fix:** Removed the line entirely. `serialize_booking()` already provides the correct `start_time`.

## Bug 13 — Cache Invalidation: Cross-Invalidation Missing
- **File/Line:** `app/routers/bookings.py`, lines 121 and 217
- **Difficulty:** Medium
- **Bug:** On booking creation, only the availability cache is invalidated (not the usage report cache). On cancellation, only the report cache is invalidated (not the availability cache). Both events affect both caches, causing stale data.
- **Fix:** Added `cache.invalidate_report(user.org_id)` after creation and `cache.invalidate_availability(booking.room_id, ...)` after cancellation.

## Bug 14 — Stats: TOCTOU Race Condition
- **File/Line:** `app/services/stats.py`, lines 15-26
- **Difficulty:** Hard
- **Bug:** `record_create` and `record_cancel` both read the current dict value, sleep 0.1s (`_aggregate_pause`), then write back. Under concurrent requests, multiple threads read the same stale value and overwrite each other's updates.
- **Fix:** Replaced the in-memory counter entirely with direct database queries (`func.count`, `func.sum`) so stats are always consistent with actual bookings, as the spec requires.

## Bug 15 — Double-Booking: Wrong Overlap Operator + Concurrency Race
- **File/Line:** `app/routers/bookings.py`, lines 42-52
- **Difficulty:** Hard
- **Bug (logic):** Overlap check used `<=` (`b.start_time <= end and start <= b.end_time`) which blocks back-to-back bookings. Spec says: "existing.start < new.end AND new.start < existing.end" (strict `<`).
- **Bug (concurrency):** The check loads all bookings, calls `_pricing_warmup()` (sleeps 0.12s), then returns. The insert happens after the function returns. Two concurrent requests can both pass the check before either inserts.
- **Fix:** Changed `<=` to strict `<`, moved the overlap check to a database query, and wrapped the check-and-insert in a `write_lock` so only one thread can create at a time.

## Bug 16 — Booking Quota: Concurrency Race
- **File/Line:** `app/routers/bookings.py`, lines 55-71
- **Difficulty:** Hard
- **Bug:** Same TOCTOU race as the conflict check — `_check_quota` counts existing bookings, calls `_quota_audit()` (sleeps 0.1s), then checks the count. Multiple concurrent requests all see the same count and all pass.
- **Fix:** Wrapped inside the same `write_lock` used for booking creation, serializing the quota check with the insert.

## Bug 17 — Rate Limiter: Concurrency Race
- **File/Line:** `app/services/ratelimit.py`, lines 18-26
- **Difficulty:** Hard
- **Bug:** Reads the bucket, calls `_settle_pause()` (sleeps 0.1s), then appends and checks length. Concurrent requests all read the same bucket length, all pass, then all append.
- **Fix:** Wrapped the entire read-append-check sequence in a `threading.Lock()`.

## Bug 18 — Reference Code: Concurrency Race → Duplicate Codes
- **File/Line:** `app/services/reference.py`, lines 17-21
- **Difficulty:** Hard
- **Bug:** Reads `_counter["value"]`, calls `_format_pause()` (sleeps 0.12s), then writes `current + 1`. Two concurrent calls read the same counter value and produce identical reference codes.
- **Fix:** Wrapped the read-increment-format sequence in a `threading.Lock()`, removed the sleep.

## Bug 19 — Cancel: Double-Cancel Race Condition
- **File/Line:** `app/routers/bookings.py`, lines 195-214
- **Difficulty:** Hard
- **Bug:** The `status == "cancelled"` check and `status = "cancelled"` write are not atomic. Two concurrent cancel requests both read "confirmed", both pass the check, both create RefundLog entries, and both succeed — creating duplicate refunds.
- **Fix:** Wrapped the entire cancel flow (status check + refund log + status write + commit) in the `write_lock`. Also moved the refund `db.commit()` out of `log_refund()` so the status change and refund log are committed atomically.

## Bug 20 — ABBA Deadlock in Notifications
- **File/Line:** `app/services/notifications.py`, lines 24-35
- **Difficulty:** Hard
- **Bug:** `notify_created` acquires `_email_lock` then `_audit_lock` (nested). `notify_cancelled` acquires `_audit_lock` then `_email_lock` (opposite order). This is a classic ABBA deadlock: under concurrent create + cancel, each thread holds one lock and waits for the other forever, hanging the service.
- **Fix:** Changed both functions to use consistent lock ordering: acquire `_email_lock` first, release it, then acquire `_audit_lock`. No nested locking.

## Bug 21 — Export: Cross-Organization Data Leak
- **File/Line:** `app/services/export.py`, lines 48-50
- **Difficulty:** Medium
- **Bug:** When `include_all=True` and `room_id` is specified, the code calls `fetch_bookings_raw(db, room_id)` which filters only by `room_id` with no `org_id` check. An admin from organization A could export all bookings for a room belonging to organization B.
- **Fix:** Changed to always use `_fetch_scoped(db, org_id, None, room_id)` which applies the organization filter.

## Performance & Speed Optimizations (Response Time Tuning)

### Optimization 1 — Asynchronous Notification Dispatching
- **File/Line:** `app/services/notifications.py`, lines 10-36
- **Problem:** When creating or cancelling a booking, the main request thread was blocked on sending emails and writing audits (`time.sleep(0.12)` and `time.sleep(0.1)`), which added a baseline latency of 220ms per write request.
- **Fix:** Introduced a `ThreadPoolExecutor` within the notifications service. Calls to `notify_created` and `notify_cancelled` are submitted to background worker threads, allowing the main thread to immediately return the HTTP response without waiting for the simulated email/audit logs.

### Optimization 2 — SQLite Database WAL (Write-Ahead Logging) Mode
- **File/Line:** `app/database.py`, lines 12-21
- **Problem:** Default SQLite database mode blocks concurrent readers during write transactions, slowing down queries under load.
- **Fix:** Added a connection event listener to configure the SQLite database connection using `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL`. This allows concurrent reads while writes are active and speeds up commit disk synchronization.


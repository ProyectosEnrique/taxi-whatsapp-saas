"""
In-memory store: {ride_id: [(telegram_chat_id, message_id), ...]}
Used to edit driver notifications when a ride is taken.
Single-process deployment — no Redis needed.
"""

_store: dict[str, list[tuple[str, int]]] = {}


def save(ride_id: str, notifications: list[tuple[str, int]]) -> None:
    _store[ride_id] = notifications


def get(ride_id: str) -> list[tuple[str, int]]:
    return _store.get(ride_id, [])


def remove(ride_id: str) -> None:
    _store.pop(ride_id, None)

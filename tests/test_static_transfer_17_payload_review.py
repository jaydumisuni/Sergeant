from __future__ import annotations

from pathlib import Path

from main_review.static_transfer_17_review import run_static_transfer_17_review


ROOT = "lower-quality-payload-can-overwrite-higher-quality-cache-entry"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_quality_sensitive_upsert_requires_atomic_guard(tmp_path: Path) -> None:
    source = tmp_path / "cache.py"
    source.write_text(
        '''
OPAQUE_TYPE = "m.room.encrypted"
async def write_events(db, serialized_events):
    await db.executemany(
        """
        INSERT INTO events(event_id, event_json) VALUES (?, ?)
        ON CONFLICT(event_id) DO UPDATE SET event_json = excluded.event_json
        """,
        [(event.event_id, event.event_json) for event in serialized_events],
    )
''',
        encoding="utf-8",
    )

    result = run_static_transfer_17_review(tmp_path, ["cache.py"])

    assert ROOT in _roots(result)


def test_atomic_quality_guard_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "cache.py"
    source.write_text(
        '''
OPAQUE_TYPE = "m.room.encrypted"
async def write_events(db, event):
    await db.execute(
        """
        INSERT INTO events(event_id, event_json) VALUES (?, ?)
        ON CONFLICT(event_id) DO UPDATE SET event_json = excluded.event_json
        WHERE json_extract(events.event_json, '$.type') = 'm.room.encrypted'
           OR json_extract(excluded.event_json, '$.type') <> 'm.room.encrypted'
        RETURNING event_id
        """,
        (event.event_id, event.event_json),
    )
''',
        encoding="utf-8",
    )

    result = run_static_transfer_17_review(tmp_path, ["cache.py"])

    assert ROOT not in _roots(result)


def test_generic_upsert_without_payload_quality_classes_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "settings.py"
    source.write_text(
        '''
async def save_setting(db, key, content):
    await db.execute(
        """
        INSERT INTO settings(key, content) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET content = excluded.content
        """,
        (key, content),
    )
''',
        encoding="utf-8",
    )

    result = run_static_transfer_17_review(tmp_path, ["settings.py"])

    assert ROOT not in _roots(result)

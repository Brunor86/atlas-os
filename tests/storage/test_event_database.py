from atlas.storage.database import Database


def test_close_event_removes_event_from_active_set(tmp_path):

    database = Database(
        tmp_path / "events.db"
    )

    database.save_event(
        "warning",
        "Synthetic event",
        "temporary event",
        "2026-09-17T19:00:00",
        "2026-09-17T19:00:00",
        "open",
        "synthetic_event",
        "warning",
        "system",
        1,
        "synthetic-asset",
    )

    active = database.get_active_events()

    assert len(active) == 1

    event_id = active[0]["id"]

    database.close_event(
        event_id,
        "2026-09-17T19:01:00",
    )

    assert (
        database.get_active_events()
        == []
    )

    row = database.conn.execute(
        """
        SELECT
            status,
            last_seen

        FROM events

        WHERE id = ?
        """,
        (
            event_id,
        ),
    ).fetchone()

    assert row == (
        "closed",
        "2026-09-17T19:01:00",
    )

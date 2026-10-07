import os
import sqlite3

from atlas.services.sentinel.scheduled import (
    sentinel_database_snapshot,
)


def _create_database(
    path,
):
    db = sqlite3.connect(
        path
    )

    try:
        db.execute(
            """
            CREATE TABLE sample (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        db.execute(
            """
            INSERT INTO sample(value)
            VALUES (?)
            """,
            (
                "production",
            ),
        )

        db.commit()

    finally:
        db.close()


def test_snapshot_isolated_from_source(
    tmp_path,
):
    source = (
        tmp_path
        / "production.db"
    )

    _create_database(
        source
    )

    before = (
        source.read_bytes()
    )

    with sentinel_database_snapshot(
        source,
        directory=tmp_path,
    ) as snapshot:

        assert snapshot.exists()

        assert (
            os.environ[
                "ATLAS_DB_PATH"
            ]
            == str(snapshot)
        )

        db = sqlite3.connect(
            snapshot
        )

        try:
            db.execute(
                """
                INSERT INTO sample(value)
                VALUES (?)
                """,
                (
                    "sentinel-write",
                ),
            )

            db.commit()

        finally:
            db.close()

        source_db = sqlite3.connect(
            f"file:{source}?mode=ro",
            uri=True,
        )

        try:
            count = source_db.execute(
                """
                SELECT COUNT(*)
                FROM sample
                """
            ).fetchone()[0]

        finally:
            source_db.close()

        assert count == 1

    assert not snapshot.exists()

    after = (
        source.read_bytes()
    )

    assert after == before


def test_previous_database_environment_restored(
    tmp_path,
    monkeypatch,
):
    source = (
        tmp_path
        / "production.db"
    )

    _create_database(
        source
    )

    monkeypatch.setenv(
        "ATLAS_DB_PATH",
        "/previous/database.db",
    )

    with sentinel_database_snapshot(
        source,
        directory=tmp_path,
    ):
        assert (
            os.environ[
                "ATLAS_DB_PATH"
            ]
            != "/previous/database.db"
        )

    assert (
        os.environ[
            "ATLAS_DB_PATH"
        ]
        == "/previous/database.db"
    )

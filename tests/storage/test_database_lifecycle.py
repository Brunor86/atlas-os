import sqlite3

import pytest

from atlas.storage.database import Database


def assert_connection_closed(connection):

    with pytest.raises(
        sqlite3.ProgrammingError
    ):
        connection.execute(
            "SELECT 1"
        )


def test_database_close_is_idempotent(
    tmp_path,
):

    database = Database(
        tmp_path / "atlas.db"
    )

    connection = database.conn

    database.close()
    database.close()

    assert_connection_closed(
        connection
    )


def test_database_context_manager_closes_connection(
    tmp_path,
):

    with Database(
        tmp_path / "atlas.db"
    ) as database:

        connection = database.conn

        assert (
            connection.execute(
                "SELECT 1"
            ).fetchone()[0]
            == 1
        )

    assert_connection_closed(
        connection
    )


def test_database_finalizer_closes_connection(
    tmp_path,
):

    database = Database(
        tmp_path / "atlas.db"
    )

    connection = database.conn

    del database

    assert_connection_closed(
        connection
    )

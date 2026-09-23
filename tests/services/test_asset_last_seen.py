from datetime import (
    UTC,
    datetime,
)

from atlas.core.asset import (
    Asset,
    AssetStatus,
    AssetType,
    Criticality,
)

from atlas.core.identity import (
    AssetIdentity,
)

from atlas.storage.asset_repository import (
    AssetRepository,
)


def test_asset_repository_restores_last_seen(
    tmp_path,
    monkeypatch,
):

    database = (
        tmp_path
        / "atlas.db"
    )

    monkeypatch.setenv(
        "ATLAS_DB_PATH",
        str(database),
    )

    repository = AssetRepository()

    last_seen = datetime(
        2026,
        9,
        18,
        3,
        17,
        0,
        181347,
        tzinfo=UTC,
    )

    asset = Asset(
        id="application-docker-test",
        name="test-container",
        type=AssetType.APPLICATION,
        identity=AssetIdentity(
            serial="test-container",
            vendor="Docker",
        ),
        status=AssetStatus.ONLINE,
        health=100.0,
        criticality=Criticality.HIGH,
        last_seen=last_seen,
    )

    repository.save_asset(
        asset
    )

    loaded = repository.get_asset(
        asset.id
    )

    assert loaded is not None

    assert (
        loaded.last_seen
        == last_seen
    )

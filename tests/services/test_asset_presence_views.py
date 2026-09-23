from datetime import (
    UTC,
    datetime,
)

from atlas.core.asset import (
    Asset,
    AssetPresence,
    AssetStatus,
    AssetType,
)

from atlas.core.identity import (
    AssetIdentity,
)

from atlas.services.assets.api import (
    AssetAPIService,
)

from atlas.storage.asset_repository import (
    AssetRepository,
)


NOW = datetime(
    2026,
    9,
    20,
    3,
    10,
    tzinfo=UTC,
)


def make_asset(
    asset_id,
    *,
    name=None,
    identity=None,
):

    return Asset(
        id=asset_id,
        name=(
            name
            or asset_id
        ),
        type=AssetType.SERVER,
        status=AssetStatus.ONLINE,
        health=100.0,
        last_seen=NOW,
        identity=(
            identity
            or AssetIdentity()
        ),
    )


def test_asset_api_default_views_only_include_active_inventory(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setenv(
        "ATLAS_DB_PATH",
        str(
            tmp_path
            / "atlas.db"
        ),
    )

    repository = (
        AssetRepository()
    )

    active = make_asset(
        "active-server"
    )

    retired = make_asset(
        "retired-server"
    )

    repository.save_asset(
        active
    )

    repository.save_asset(
        retired
    )

    repository.set_presence(
        retired.id,
        AssetPresence.RETIRED,
        reason="test retirement",
        changed_at=NOW,
    )

    service = (
        AssetAPIService()
    )

    service.repository = (
        repository
    )

    assets = (
        service.list_assets()
    )

    ids = {
        item["id"]
        for item
        in assets
    }

    assert ids == {
        active.id
    }

    assert assets[0][
        "presence"
    ] == "ACTIVE"

    overview = (
        service.overview()
    )

    assert overview[
        "summary"
    ][
        "total"
    ] == 1


def test_asset_detail_preserves_retired_history(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setenv(
        "ATLAS_DB_PATH",
        str(
            tmp_path
            / "atlas.db"
        ),
    )

    repository = (
        AssetRepository()
    )

    retired = make_asset(
        "retired-server"
    )

    repository.save_asset(
        retired
    )

    repository.set_presence(
        retired.id,
        AssetPresence.RETIRED,
        reason="test retirement",
        changed_at=NOW,
    )

    service = (
        AssetAPIService()
    )

    service.repository = (
        repository
    )

    detail = (
        service.get_asset(
            retired.id
        )
    )

    assert detail is not None

    assert detail[
        "presence"
    ] == "RETIRED"

    assert (
        detail[
            "presence_changed_at"
        ]
        == NOW.isoformat()
    )


def test_find_by_identity_prefers_active_over_retired_duplicate(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setenv(
        "ATLAS_DB_PATH",
        str(
            tmp_path
            / "atlas.db"
        ),
    )

    repository = (
        AssetRepository()
    )

    identity = AssetIdentity(
        serial="SAME-SERIAL",
        model="same-model",
        vendor="same-vendor",
        firmware="same-firmware",
        device="/dev/test",
    )

    retired = make_asset(
        "aaa-retired",
        identity=identity,
    )

    active = make_asset(
        "zzz-active",
        identity=identity,
    )

    repository.save_asset(
        retired
    )

    repository.save_asset(
        active
    )

    repository.set_presence(
        retired.id,
        AssetPresence.RETIRED,
        reason="legacy identity",
        changed_at=NOW,
    )

    resolved = (
        repository.find_by_identity(
            identity
        )
    )

    assert (
        resolved
        == active.id
    )

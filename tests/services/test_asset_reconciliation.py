from datetime import (
    UTC,
    datetime,
    timedelta,
)

from atlas.core.asset import (
    Asset,
    AssetPresence,
    AssetStatus,
    AssetType,
)

from atlas.storage.asset_repository import (
    AssetRepository,
)

from atlas.services.assets.reconciliation import (
    AssetReconciliationService,
)


NOW = datetime(
    2026,
    9,
    20,
    3,
    0,
    tzinfo=UTC,
)


def make_asset(
    asset_id,
    *,
    last_seen=None,
):

    return Asset(
        id=asset_id,
        name=asset_id,
        type=AssetType.SERVER,
        status=AssetStatus.ONLINE,
        health=100.0,
        last_seen=(
            last_seen
            or NOW
        ),
    )


def test_missing_active_asset_becomes_stale(
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

    asset = make_asset(
        "missing-server",
        last_seen=(
            NOW
            - timedelta(
                days=10
            )
        ),
    )

    repository.save_asset(
        asset
    )

    service = (
        AssetReconciliationService(
            repository=repository,
            clock=lambda: NOW,
        )
    )

    result = (
        service.reconcile([])
    )

    loaded = (
        repository.get_asset(
            asset.id
        )
    )

    assert (
        loaded.presence
        == AssetPresence.STALE
    )

    assert result["counts"][
        "STALE"
    ] == 1

    events = (
        repository.get_presence_events(
            asset.id
        )
    )

    assert len(events) == 1

    assert events[0][
        "from_presence"
    ] == "ACTIVE"

    assert events[0][
        "to_presence"
    ] == "STALE"


def test_old_last_seen_does_not_bypass_stale_grace_window(
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

    asset = make_asset(
        "old-server",
        last_seen=(
            NOW
            - timedelta(
                days=30
            )
        ),
    )

    repository.save_asset(
        asset
    )

    clock = {
        "now": NOW
    }

    service = (
        AssetReconciliationService(
            repository=repository,
            clock=lambda: clock["now"],
        )
    )

    #
    # First authoritative absence:
    # ACTIVE -> STALE.
    #
    service.reconcile([])

    loaded = (
        repository.get_asset(
            asset.id
        )
    )

    assert (
        loaded.presence
        == AssetPresence.STALE
    )

    assert (
        loaded.presence_changed_at
        == NOW
    )

    #
    # Even though last_seen is 30 days old, another immediate
    # complete cycle must NOT retire the asset.
    #
    result = (
        service.reconcile([])
    )

    assert result["counts"][
        "STALE"
    ] == 1

    assert result["counts"][
        "RETIRED"
    ] == 0

    assert len(
        repository.get_presence_events(
            asset.id
        )
    ) == 1

    #
    # Still inside the seven-day grace window.
    #
    clock["now"] = (
        NOW
        + timedelta(
            days=7
        )
        - timedelta(
            seconds=1
        )
    )

    service.reconcile([])

    loaded = (
        repository.get_asset(
            asset.id
        )
    )

    assert (
        loaded.presence
        == AssetPresence.STALE
    )

    #
    # Exactly seven days after the STALE transition,
    # retirement becomes valid.
    #
    clock["now"] = (
        NOW
        + timedelta(
            days=7
        )
    )

    result = (
        service.reconcile([])
    )

    loaded = (
        repository.get_asset(
            asset.id
        )
    )

    assert (
        loaded.presence
        == AssetPresence.RETIRED
    )

    assert result["counts"][
        "RETIRED"
    ] == 1

    events = (
        repository.get_presence_events(
            asset.id
        )
    )

    assert [
        (
            event["from_presence"],
            event["to_presence"],
        )
        for event in events
    ] == [
        (
            "ACTIVE",
            "STALE",
        ),
        (
            "STALE",
            "RETIRED",
        ),
    ]


def test_recent_stale_asset_does_not_retire_early(
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

    asset = make_asset(
        "recent-server",
        last_seen=(
            NOW
            - timedelta(
                days=1
            )
        ),
    )

    repository.save_asset(
        asset
    )

    service = (
        AssetReconciliationService(
            repository=repository,
            clock=lambda: NOW,
        )
    )

    service.reconcile([])
    service.reconcile([])

    loaded = (
        repository.get_asset(
            asset.id
        )
    )

    assert (
        loaded.presence
        == AssetPresence.STALE
    )

    assert len(
        repository.get_presence_events(
            asset.id
        )
    ) == 1


def test_rediscovered_retired_asset_becomes_active(
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

    asset = make_asset(
        "returning-server",
        last_seen=(
            NOW
            - timedelta(
                days=10
            )
        ),
    )

    repository.save_asset(
        asset
    )

    repository.set_presence(
        asset.id,
        AssetPresence.RETIRED,
        reason="test setup",
        changed_at=NOW,
    )

    service = (
        AssetReconciliationService(
            repository=repository,
            clock=lambda: NOW,
        )
    )

    result = service.reconcile(
        [
            asset
        ]
    )

    loaded = (
        repository.get_asset(
            asset.id
        )
    )

    assert (
        loaded.presence
        == AssetPresence.ACTIVE
    )

    assert result["counts"][
        "ACTIVE"
    ] == 1

    events = (
        repository.get_presence_events(
            asset.id
        )
    )

    assert events[-1][
        "to_presence"
    ] == "ACTIVE"


def test_reconciliation_is_idempotent_for_unchanged_active_asset(
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

    asset = make_asset(
        "active-server"
    )

    repository.save_asset(
        asset
    )

    service = (
        AssetReconciliationService(
            repository=repository,
            clock=lambda: NOW,
        )
    )

    service.reconcile(
        [
            asset
        ]
    )

    service.reconcile(
        [
            asset
        ]
    )

    assert (
        repository.get_presence_events(
            asset.id
        )
        == []
    )


def test_discovery_persistence_does_not_silently_reactivate_retired_asset(
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

    asset = make_asset(
        "preserved-retired"
    )

    repository.save_asset(
        asset
    )

    repository.set_presence(
        asset.id,
        AssetPresence.RETIRED,
        reason="test setup",
        changed_at=NOW,
    )

    #
    # Normal Discovery persistence must preserve the existing
    # lifecycle state. Only authoritative reconciliation may
    # reactivate it.
    #
    repository.save_asset(
        make_asset(
            asset.id
        )
    )

    loaded = (
        repository.get_asset(
            asset.id
        )
    )

    assert (
        loaded.presence
        == AssetPresence.RETIRED
    )


def test_rediscovery_resets_future_retirement_grace_window(
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

    asset = make_asset(
        "flapping-server",
        last_seen=(
            NOW
            - timedelta(
                days=30
            )
        ),
    )

    repository.save_asset(
        asset
    )

    clock = {
        "now": NOW
    }

    service = (
        AssetReconciliationService(
            repository=repository,
            clock=lambda: clock["now"],
        )
    )

    #
    # First absence.
    #
    service.reconcile([])

    loaded = repository.get_asset(
        asset.id
    )

    assert (
        loaded.presence
        == AssetPresence.STALE
    )

    assert (
        loaded.presence_changed_at
        == NOW
    )

    #
    # Rediscovered three days later.
    #
    clock["now"] = (
        NOW
        + timedelta(
            days=3
        )
    )

    service.reconcile(
        [asset]
    )

    loaded = repository.get_asset(
        asset.id
    )

    assert (
        loaded.presence
        == AssetPresence.ACTIVE
    )

    assert (
        loaded.presence_changed_at
        == clock["now"]
    )

    #
    # Missing again one day later.
    # This creates a NEW grace window.
    #
    clock["now"] = (
        NOW
        + timedelta(
            days=4
        )
    )

    service.reconcile([])

    loaded = repository.get_asset(
        asset.id
    )

    assert (
        loaded.presence
        == AssetPresence.STALE
    )

    second_stale_at = (
        loaded.presence_changed_at
    )

    assert (
        second_stale_at
        == clock["now"]
    )

    #
    # Six days after the new STALE transition:
    # must still be STALE.
    #
    clock["now"] = (
        NOW
        + timedelta(
            days=10
        )
    )

    service.reconcile([])

    loaded = repository.get_asset(
        asset.id
    )

    assert (
        loaded.presence
        == AssetPresence.STALE
    )

    #
    # Seven days after the NEW STALE transition:
    # now it may retire.
    #
    clock["now"] = (
        NOW
        + timedelta(
            days=11
        )
    )

    service.reconcile([])

    loaded = repository.get_asset(
        asset.id
    )

    assert (
        loaded.presence
        == AssetPresence.RETIRED
    )

    events = (
        repository.get_presence_events(
            asset.id
        )
    )

    assert [
        (
            event["from_presence"],
            event["to_presence"],
        )
        for event in events
    ] == [
        (
            "ACTIVE",
            "STALE",
        ),
        (
            "STALE",
            "ACTIVE",
        ),
        (
            "ACTIVE",
            "STALE",
        ),
        (
            "STALE",
            "RETIRED",
        ),
    ]

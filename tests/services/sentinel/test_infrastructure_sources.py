from types import SimpleNamespace

from atlas.services.sentinel.contracts import (
    SentinelSeverity,
)
from atlas.services.sentinel.infrastructure_sources import (
    CriticalAssetStateSource,
    StorageHealthSource,
)


def _enum(name):
    return SimpleNamespace(
        name=name
    )


def _asset(
    *,
    asset_id="asset-1",
    name="asset",
    asset_type="STORAGE",
    status="ONLINE",
    presence="ACTIVE",
    criticality="MEDIUM",
    metadata=None,
):
    return SimpleNamespace(
        id=asset_id,
        name=name,
        type=_enum(
            asset_type
        ),
        status=_enum(
            status
        ),
        presence=_enum(
            presence
        ),
        criticality=_enum(
            criticality
        ),
        metadata=(
            metadata
            or {}
        ),
    )


class FakeRepository:

    def __init__(
        self,
        assets,
    ):
        self.assets = list(
            assets
        )

    def get_all_assets(self):
        return list(
            self.assets
        )


def test_storage_temperature_below_warning_is_silent():
    source = StorageHealthSource(
        repository=FakeRepository(
            [
                _asset(
                    metadata={
                        "temperature_c": 49,
                        "smart_available": True,
                        "smart_passed": True,
                    }
                )
            ]
        )
    )

    assert source.collect() == []


def test_storage_temperature_warning():
    source = StorageHealthSource(
        repository=FakeRepository(
            [
                _asset(
                    metadata={
                        "temperature_c": 50,
                        "smart_available": True,
                        "smart_passed": True,
                    }
                )
            ]
        )
    )

    findings = source.collect()

    assert len(findings) == 1
    assert (
        findings[0].severity
        == SentinelSeverity.WARNING
    )
    assert findings[0].kind == "storage_health"


def test_storage_temperature_critical():
    source = StorageHealthSource(
        repository=FakeRepository(
            [
                _asset(
                    metadata={
                        "temperature_c": 60,
                        "smart_available": True,
                        "smart_passed": True,
                    }
                )
            ]
        )
    )

    findings = source.collect()

    assert len(findings) == 1
    assert (
        findings[0].severity
        == SentinelSeverity.CRITICAL
    )


def test_storage_smart_failure_is_critical():
    source = StorageHealthSource(
        repository=FakeRepository(
            [
                _asset(
                    metadata={
                        "temperature_c": 35,
                        "smart_available": True,
                        "smart_passed": False,
                        "health": "FAILED",
                    }
                )
            ]
        )
    )

    findings = source.collect()

    assert len(findings) == 1
    assert (
        findings[0].severity
        == SentinelSeverity.CRITICAL
    )


def test_non_active_storage_is_ignored():
    source = StorageHealthSource(
        repository=FakeRepository(
            [
                _asset(
                    presence="RETIRED",
                    metadata={
                        "temperature_c": 70,
                        "smart_available": True,
                        "smart_passed": False,
                    },
                )
            ]
        )
    )

    assert source.collect() == []


def test_high_stale_asset_warns():
    source = CriticalAssetStateSource(
        repository=FakeRepository(
            [
                _asset(
                    asset_type="VM",
                    criticality="HIGH",
                    presence="STALE",
                    status="ONLINE",
                )
            ]
        )
    )

    findings = source.collect()

    assert len(findings) == 1
    assert (
        findings[0].severity
        == SentinelSeverity.WARNING
    )


def test_high_degraded_asset_warns():
    source = CriticalAssetStateSource(
        repository=FakeRepository(
            [
                _asset(
                    asset_type="SERVER",
                    criticality="HIGH",
                    presence="ACTIVE",
                    status="DEGRADED",
                )
            ]
        )
    )

    findings = source.collect()

    assert len(findings) == 1
    assert (
        findings[0].kind
        == "critical_asset_state"
    )


def test_high_offline_asset_is_deliberately_silent():
    source = CriticalAssetStateSource(
        repository=FakeRepository(
            [
                _asset(
                    asset_type="VM",
                    criticality="HIGH",
                    presence="ACTIVE",
                    status="OFFLINE",
                )
            ]
        )
    )

    assert source.collect() == []


def test_medium_stale_asset_is_silent():
    source = CriticalAssetStateSource(
        repository=FakeRepository(
            [
                _asset(
                    asset_type="APPLICATION",
                    criticality="MEDIUM",
                    presence="STALE",
                    status="OFFLINE",
                )
            ]
        )
    )

    assert source.collect() == []


def test_explicitly_managed_asset_is_excluded_from_generic_critical_source():
    source = CriticalAssetStateSource(
        repository=FakeRepository(
            [
                _asset(
                    asset_id="managed-vm",
                    asset_type="VM",
                    criticality="HIGH",
                    presence="STALE",
                    status="DEGRADED",
                )
            ]
        ),
        excluded_asset_ids={
            "managed-vm",
        },
    )

    assert source.collect() == []

from types import SimpleNamespace

from atlas.core.asset import (
    Asset,
    AssetStatus,
    AssetType,
)
from atlas.services.noc.asset_health import (
    AssetHealthAnalyzer,
)


def make_asset(status, observations=None):

    asset = Asset(
        id="test-asset",
        name="test",
        type=AssetType.STORAGE,
        status=status,
    )

    asset.observations = observations or []

    return asset


def observation(
    observation_type,
    value,
    severity="info",
):

    return SimpleNamespace(
        type=observation_type,
        value=value,
        severity=severity,
    )


def test_online_asset_has_full_health():

    analyzer = AssetHealthAnalyzer()

    asset = make_asset(
        AssetStatus.ONLINE
    )

    findings = analyzer.analyze(asset)

    assert analyzer.evaluate_health(
        asset,
        findings,
    ) == 100.0


def test_degraded_asset_has_baseline_health():

    analyzer = AssetHealthAnalyzer()

    asset = make_asset(
        AssetStatus.DEGRADED
    )

    findings = analyzer.analyze(asset)

    assert analyzer.evaluate_health(
        asset,
        findings,
    ) == 40.0


def test_offline_asset_has_zero_health():

    analyzer = AssetHealthAnalyzer()

    asset = make_asset(
        AssetStatus.OFFLINE
    )

    findings = analyzer.analyze(asset)

    assert analyzer.evaluate_health(
        asset,
        findings,
    ) == 0.0


def test_unknown_asset_has_zero_health():

    analyzer = AssetHealthAnalyzer()

    asset = make_asset(
        AssetStatus.UNKNOWN
    )

    findings = analyzer.analyze(asset)

    assert analyzer.evaluate_health(
        asset,
        findings,
    ) == 0.0


def test_warning_finding_reduces_online_health():

    analyzer = AssetHealthAnalyzer()

    asset = make_asset(
        AssetStatus.ONLINE,
        [
            observation(
                "temperature",
                55,
            )
        ],
    )

    findings = analyzer.analyze(asset)

    assert len(findings) == 1
    assert findings[0].severity == "WARNING"

    assert analyzer.evaluate_health(
        asset,
        findings,
    ) == 60.0


def test_critical_finding_reduces_online_health_to_zero():

    analyzer = AssetHealthAnalyzer()

    asset = make_asset(
        AssetStatus.ONLINE,
        [
            observation(
                "smart",
                "FAILED",
            )
        ],
    )

    findings = analyzer.analyze(asset)

    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"

    assert analyzer.evaluate_health(
        asset,
        findings,
    ) == 0.0


def test_evaluate_updates_asset_health():

    analyzer = AssetHealthAnalyzer()

    asset = make_asset(
        AssetStatus.ONLINE,
        [
            observation(
                "temperature",
                55,
            )
        ],
    )

    findings = analyzer.evaluate(asset)

    assert len(findings) == 1
    assert asset.health == 60.0

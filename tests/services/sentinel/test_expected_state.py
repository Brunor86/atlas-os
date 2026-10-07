from pathlib import Path
from types import SimpleNamespace

import pytest

from atlas.services.sentinel.contracts import (
    SentinelSeverity,
)
from atlas.services.sentinel.expected_state import (
    ExpectedAssetRule,
    ExpectedAssetStateSource,
    ExpectedStatePolicy,
    load_expected_state_policy,
)


def _enum(name):
    return SimpleNamespace(
        name=name
    )


def _asset(
    *,
    asset_id,
    status="ONLINE",
    presence="ACTIVE",
):
    return SimpleNamespace(
        id=asset_id,
        status=_enum(
            status
        ),
        presence=_enum(
            presence
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


def _policy(
    *rules,
):
    return ExpectedStatePolicy(
        version=1,
        assets=tuple(
            rules
        ),
    )


def _rule(
    asset_id="asset-1",
    *,
    status="ONLINE",
    severity=(
        SentinelSeverity.WARNING
    ),
):
    return ExpectedAssetRule(
        asset_id=asset_id,
        label=asset_id,
        expected_status=status,
        severity=severity,
    )


def test_expected_online_is_silent():
    source = ExpectedAssetStateSource(
        repository=FakeRepository(
            [
                _asset(
                    asset_id="asset-1",
                    status="ONLINE",
                )
            ]
        ),
        policy=_policy(
            _rule()
        ),
    )

    assert source.collect() == []


def test_expected_online_but_offline_warns():
    source = ExpectedAssetStateSource(
        repository=FakeRepository(
            [
                _asset(
                    asset_id="asset-1",
                    status="OFFLINE",
                )
            ]
        ),
        policy=_policy(
            _rule()
        ),
    )

    findings = source.collect()

    assert len(findings) == 1

    assert (
        findings[0].severity
        == SentinelSeverity.WARNING
    )

    assert (
        findings[0].kind
        == "expected_asset_state"
    )


def test_missing_expected_asset_warns():
    source = ExpectedAssetStateSource(
        repository=FakeRepository(
            []
        ),
        policy=_policy(
            _rule()
        ),
    )

    findings = source.collect()

    assert len(findings) == 1

    assert (
        findings[0]
        .evidence[
            "actual_status"
        ]
        == "MISSING"
    )


def test_stale_expected_asset_warns():
    source = ExpectedAssetStateSource(
        repository=FakeRepository(
            [
                _asset(
                    asset_id="asset-1",
                    status="ONLINE",
                    presence="STALE",
                )
            ]
        ),
        policy=_policy(
            _rule()
        ),
    )

    assert len(
        source.collect()
    ) == 1


def test_unlisted_offline_asset_is_silent():
    source = ExpectedAssetStateSource(
        repository=FakeRepository(
            [
                _asset(
                    asset_id="optional-vm",
                    status="OFFLINE",
                )
            ]
        ),
        policy=_policy(),
    )

    assert source.collect() == []


def test_rule_severity_is_preserved():
    source = ExpectedAssetStateSource(
        repository=FakeRepository(
            [
                _asset(
                    asset_id="atlas-host",
                    status="OFFLINE",
                )
            ]
        ),
        policy=_policy(
            _rule(
                "atlas-host",
                severity=(
                    SentinelSeverity.CRITICAL
                ),
            )
        ),
    )

    findings = source.collect()

    assert (
        findings[0].severity
        == SentinelSeverity.CRITICAL
    )


def test_policy_loader(
    tmp_path,
):
    path = (
        tmp_path
        / "policy.toml"
    )

    path.write_text(
        """
version = 1

[[assets]]
id = "asset-1"
label = "Asset One"
expected_status = "ONLINE"
severity = "CRITICAL"
""".strip()
        + "\n"
    )

    policy = (
        load_expected_state_policy(
            path
        )
    )

    assert policy.version == 1
    assert len(policy.assets) == 1

    rule = policy.assets[0]

    assert rule.asset_id == "asset-1"
    assert (
        rule.expected_status
        == "ONLINE"
    )
    assert (
        rule.severity
        == SentinelSeverity.CRITICAL
    )


def test_policy_rejects_duplicate_assets(
    tmp_path,
):
    path = (
        tmp_path
        / "policy.toml"
    )

    path.write_text(
        """
version = 1

[[assets]]
id = "asset-1"

[[assets]]
id = "asset-1"
""".strip()
        + "\n"
    )

    with pytest.raises(
        ValueError,
        match="Duplicate",
    ):
        load_expected_state_policy(
            path
        )


def test_policy_rejects_info_severity(
    tmp_path,
):
    path = (
        tmp_path
        / "policy.toml"
    )

    path.write_text(
        """
version = 1

[[assets]]
id = "asset-1"
severity = "INFO"
""".strip()
        + "\n"
    )

    with pytest.raises(
        ValueError,
        match="WARNING or CRITICAL",
    ):
        load_expected_state_policy(
            path
        )

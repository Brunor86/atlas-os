import os
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from atlas.services.sentinel.contracts import (
    SentinelFinding,
    SentinelSeverity,
    SentinelState,
)
from atlas.services.sentinel.fingerprint import (
    sentinel_fingerprint,
)
from atlas.storage.asset_repository import (
    AssetRepository,
)


DEFAULT_POLICY_PATH = (
    "/etc/atlas/"
    "sentinel-expectations.toml"
)


def _now():
    return datetime.now(UTC)


def _enum_name(value):
    if value is None:
        return ""

    name = getattr(
        value,
        "name",
        None,
    )

    if name is not None:
        return str(
            name
        ).upper()

    return str(
        value
    ).upper()


@dataclass(
    frozen=True,
    slots=True,
)
class ExpectedAssetRule:
    asset_id: str
    label: str
    expected_status: str
    severity: SentinelSeverity


@dataclass(
    frozen=True,
    slots=True,
)
class ExpectedStatePolicy:
    version: int
    assets: tuple[
        ExpectedAssetRule,
        ...
    ]

    @property
    def asset_ids(self):
        return frozenset(
            rule.asset_id
            for rule in self.assets
        )


def load_expected_state_policy(
    path=None,
):
    policy_path = Path(
        path
        or os.environ.get(
            "ATLAS_SENTINEL_EXPECTATIONS_PATH"
        )
        or DEFAULT_POLICY_PATH
    )

    if not policy_path.is_file():
        raise FileNotFoundError(
            "Sentinel expected-state policy "
            f"not found: {policy_path}"
        )

    with policy_path.open(
        "rb"
    ) as handle:
        payload = tomllib.load(
            handle
        )

    version = payload.get(
        "version"
    )

    if version != 1:
        raise ValueError(
            "Unsupported Sentinel expected-state "
            f"policy version: {version!r}"
        )

    raw_assets = payload.get(
        "assets"
    )

    if raw_assets is None:
        raw_assets = []

    if not isinstance(
        raw_assets,
        list,
    ):
        raise ValueError(
            "Expected-state assets must be "
            "a TOML array of tables"
        )

    rules = []
    seen = set()

    valid_statuses = {
        "ONLINE",
        "OFFLINE",
        "DEGRADED",
    }

    for index, raw in enumerate(
        raw_assets,
        start=1,
    ):
        if not isinstance(
            raw,
            dict,
        ):
            raise ValueError(
                f"Invalid asset rule #{index}"
            )

        asset_id = str(
            raw.get(
                "id"
            )
            or ""
        ).strip()

        if not asset_id:
            raise ValueError(
                f"Asset rule #{index} "
                "has no id"
            )

        if asset_id in seen:
            raise ValueError(
                "Duplicate expected-state "
                f"asset id: {asset_id}"
            )

        seen.add(
            asset_id
        )

        label = str(
            raw.get(
                "label"
            )
            or asset_id
        ).strip()

        expected_status = str(
            raw.get(
                "expected_status"
            )
            or "ONLINE"
        ).strip().upper()

        if (
            expected_status
            not in valid_statuses
        ):
            raise ValueError(
                f"{asset_id}: invalid "
                "expected_status "
                f"{expected_status!r}"
            )

        severity_name = str(
            raw.get(
                "severity"
            )
            or "WARNING"
        ).strip().upper()

        try:
            severity = (
                SentinelSeverity[
                    severity_name
                ]
            )
        except KeyError as exc:
            raise ValueError(
                f"{asset_id}: invalid "
                f"severity {severity_name!r}"
            ) from exc

        if (
            severity
            == SentinelSeverity.INFO
        ):
            raise ValueError(
                f"{asset_id}: expected-state "
                "rules must be WARNING "
                "or CRITICAL"
            )

        rules.append(
            ExpectedAssetRule(
                asset_id=asset_id,
                label=label,
                expected_status=(
                    expected_status
                ),
                severity=severity,
            )
        )

    return ExpectedStatePolicy(
        version=version,
        assets=tuple(
            rules
        ),
    )


class ExpectedAssetStateSource:
    """
    Compare explicitly managed assets with their
    operator-defined expected runtime state.

    Nothing is inferred.

    An asset that is not listed in the policy is
    deliberately outside expected-state monitoring.
    """

    name = "expected_asset_state"

    def __init__(
        self,
        *,
        repository=None,
        policy=None,
        policy_path=None,
    ):
        self.repository = (
            repository
            or AssetRepository()
        )

        self.policy = (
            policy
            or load_expected_state_policy(
                policy_path
            )
        )

    def collect(
        self,
        *,
        observed_at=None,
    ):
        observed_at = (
            observed_at
            or _now()
        )

        assets = {
            str(asset.id): asset
            for asset
            in self.repository.get_all_assets()
        }

        findings = []

        for rule in self.policy.assets:

            asset = assets.get(
                rule.asset_id
            )

            reasons = []

            if asset is None:
                reasons.append(
                    "Asset is missing from "
                    "the current inventory."
                )

                actual_status = (
                    "MISSING"
                )

                actual_presence = (
                    "MISSING"
                )

            else:
                actual_status = (
                    _enum_name(
                        getattr(
                            asset,
                            "status",
                            None,
                        )
                    )
                )

                actual_presence = (
                    _enum_name(
                        getattr(
                            asset,
                            "presence",
                            None,
                        )
                    )
                )

                if (
                    actual_presence
                    != "ACTIVE"
                ):
                    reasons.append(
                        "Inventory presence is "
                        f"{actual_presence or 'UNKNOWN'} "
                        "instead of ACTIVE."
                    )

                if (
                    actual_status
                    != rule.expected_status
                ):
                    reasons.append(
                        "Operational state is "
                        f"{actual_status or 'UNKNOWN'} "
                        "instead of "
                        f"{rule.expected_status}."
                    )

            if not reasons:
                continue

            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source=(
                                "infrastructure"
                            ),
                            kind=(
                                "expected_asset_state"
                            ),
                            subject=(
                                rule.asset_id
                            ),
                        )
                    ),
                    source="infrastructure",
                    kind="expected_asset_state",
                    subject=rule.asset_id,
                    severity=rule.severity,
                    state=SentinelState.OPEN,
                    title=(
                        "Expected asset state "
                        "mismatch"
                    ),
                    summary=(
                        rule.label
                        + ": "
                        + " ".join(
                            reasons
                        )
                    ),
                    observed_at=(
                        observed_at
                    ),
                    evidence={
                        "asset_id":
                            rule.asset_id,
                        "label":
                            rule.label,
                        "expected_status":
                            rule.expected_status,
                        "actual_status":
                            actual_status,
                        "actual_presence":
                            actual_presence,
                    },
                )
            )

        return findings

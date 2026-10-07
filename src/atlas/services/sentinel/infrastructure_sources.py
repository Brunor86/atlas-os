from datetime import UTC, datetime

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


def _number(value):
    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        return None

    try:
        return float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def _severity_max(
    current,
    candidate,
):
    rank = {
        SentinelSeverity.INFO: 10,
        SentinelSeverity.WARNING: 20,
        SentinelSeverity.CRITICAL: 30,
    }

    if current is None:
        return candidate

    if (
        rank[candidate]
        > rank[current]
    ):
        return candidate

    return current


class StorageHealthSource:
    """
    Interpret authoritative storage-specific telemetry.

    Do not use generic asset.health here. Storage health currently
    represents baseline asset status and can therefore be 0 even
    when SMART itself is authoritative and passing.
    """

    name = "storage_health"

    WARNING_TEMPERATURE_C = 55.0
    CRITICAL_TEMPERATURE_C = 60.0

    def __init__(
        self,
        repository=None,
    ):
        self.repository = (
            repository
            or AssetRepository()
        )

    def collect(
        self,
        *,
        observed_at=None,
    ):
        findings = []

        observed_at = (
            observed_at
            or _now()
        )

        for asset in (
            self.repository
            .get_all_assets()
        ):
            if (
                _enum_name(
                    getattr(
                        asset,
                        "type",
                        None,
                    )
                )
                != "STORAGE"
            ):
                continue

            #
            # Retired and stale historical storage records must not
            # become live alerts.
            #
            if (
                _enum_name(
                    getattr(
                        asset,
                        "presence",
                        None,
                    )
                )
                != "ACTIVE"
            ):
                continue

            metadata = (
                getattr(
                    asset,
                    "metadata",
                    None,
                )
                or {}
            )

            severity = None
            reasons = []

            temperature = _number(
                metadata.get(
                    "temperature_c"
                )
            )

            smart_available = (
                metadata.get(
                    "smart_available"
                )
            )

            smart_passed = (
                metadata.get(
                    "smart_passed"
                )
            )

            smart_health = (
                metadata.get(
                    "health"
                )
            )


            #
            # SMART failure is authoritative CRITICAL.
            #
            if (
                smart_available is True
                and smart_passed is False
            ):
                severity = (
                    SentinelSeverity.CRITICAL
                )

                reasons.append(
                    "SMART self-assessment "
                    "did not pass."
                )


            #
            # Sentinel storage temperature thresholds are calibrated
            # independently from baseline asset health:
            #
            #   >= 55 C WARNING
            #   >= 60 C CRITICAL
            #
            if (
                temperature is not None
                and temperature
                >= self.CRITICAL_TEMPERATURE_C
            ):
                severity = _severity_max(
                    severity,
                    SentinelSeverity.CRITICAL,
                )

                reasons.append(
                    f"Temperature is "
                    f"{temperature:g} °C "
                    f"(critical threshold "
                    f"{self.CRITICAL_TEMPERATURE_C:g} °C)."
                )

            elif (
                temperature is not None
                and temperature
                >= self.WARNING_TEMPERATURE_C
            ):
                severity = _severity_max(
                    severity,
                    SentinelSeverity.WARNING,
                )

                reasons.append(
                    f"Temperature is "
                    f"{temperature:g} °C "
                    f"(warning threshold "
                    f"{self.WARNING_TEMPERATURE_C:g} °C)."
                )


            if severity is None:
                continue


            asset_id = str(
                getattr(
                    asset,
                    "id",
                    "unknown-storage",
                )
            )

            asset_name = str(
                getattr(
                    asset,
                    "name",
                    asset_id,
                )
                or asset_id
            )

            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source="infrastructure",
                            kind="storage_health",
                            subject=asset_id,
                        )
                    ),
                    source="infrastructure",
                    kind="storage_health",
                    subject=asset_id,
                    severity=severity,
                    state=SentinelState.OPEN,
                    title=(
                        "Storage health "
                        "requires attention"
                    ),
                    summary=(
                        asset_name
                        + ": "
                        + " ".join(
                            reasons
                        )
                    ),
                    observed_at=observed_at,
                    evidence={
                        "asset_id":
                            asset_id,
                        "asset_name":
                            asset_name,
                        "temperature_c":
                            temperature,
                        "smart_available":
                            smart_available,
                        "smart_passed":
                            smart_passed,
                        "smart_health":
                            smart_health,
                        "warning_temperature_c":
                            (
                                self
                                .WARNING_TEMPERATURE_C
                            ),
                        "critical_temperature_c":
                            (
                                self
                                .CRITICAL_TEMPERATURE_C
                            ),
                    },
                )
            )

        return findings


class CriticalAssetStateSource:
    """
    Low-noise critical asset monitoring.

    OFFLINE is deliberately NOT actionable in v0.2 phase 1.
    We cannot infer that an asset should be running merely from
    HIGH criticality: some VMs are intentionally powered off.

    Until explicit runtime expectations exist, only authoritative
    inventory disappearance (STALE) or DEGRADED state is alertable.
    """

    name = "critical_asset_state"

    ACTIONABLE_CRITICALITY = {
        "HIGH",
        "CRITICAL",
    }

    def __init__(
        self,
        repository=None,
        excluded_asset_ids=None,
    ):
        self.repository = (
            repository
            or AssetRepository()
        )

        self.excluded_asset_ids = frozenset(
            str(asset_id)
            for asset_id
            in (
                excluded_asset_ids
                or ()
            )
        )

    def collect(
        self,
        *,
        observed_at=None,
    ):
        findings = []

        observed_at = (
            observed_at
            or _now()
        )

        for asset in (
            self.repository
            .get_all_assets()
        ):
            candidate_id = str(
                getattr(
                    asset,
                    "id",
                    "unknown-asset",
                )
            )

            if (
                candidate_id
                in self.excluded_asset_ids
            ):
                continue

            criticality = _enum_name(
                getattr(
                    asset,
                    "criticality",
                    None,
                )
            )

            if (
                criticality
                not in self.ACTIONABLE_CRITICALITY
            ):
                continue

            presence = _enum_name(
                getattr(
                    asset,
                    "presence",
                    None,
                )
            )

            status = _enum_name(
                getattr(
                    asset,
                    "status",
                    None,
                )
            )


            #
            # Historical inventory never alerts.
            #
            if presence == "RETIRED":
                continue


            reasons = []

            if presence == "STALE":
                reasons.append(
                    "Asset disappeared from "
                    "the authoritative inventory."
                )

            if status == "DEGRADED":
                reasons.append(
                    "Asset reports DEGRADED "
                    "operational state."
                )


            #
            # Critical design rule:
            #
            # OFFLINE alone is intentionally ignored until Sentinel
            # has an explicit expected-state contract.
            #
            if not reasons:
                continue


            asset_id = str(
                getattr(
                    asset,
                    "id",
                    "unknown-asset",
                )
            )

            asset_name = str(
                getattr(
                    asset,
                    "name",
                    asset_id,
                )
                or asset_id
            )


            findings.append(
                SentinelFinding(
                    fingerprint=(
                        sentinel_fingerprint(
                            source="infrastructure",
                            kind="critical_asset_state",
                            subject=asset_id,
                        )
                    ),
                    source="infrastructure",
                    kind="critical_asset_state",
                    subject=asset_id,
                    severity=(
                        SentinelSeverity.WARNING
                    ),
                    state=SentinelState.OPEN,
                    title=(
                        "Critical asset "
                        "requires attention"
                    ),
                    summary=(
                        asset_name
                        + ": "
                        + " ".join(
                            reasons
                        )
                    ),
                    observed_at=observed_at,
                    evidence={
                        "asset_id":
                            asset_id,
                        "asset_name":
                            asset_name,
                        "criticality":
                            criticality,
                        "presence":
                            presence,
                        "status":
                            status,
                    },
                )
            )

        return findings


def build_infrastructure_sources():
    """
    Build the default v0.2 infrastructure sources.

    An explicit expected-state policy has precedence over
    generic critical-asset monitoring so the same condition
    cannot generate two Sentinel findings.

    A missing default policy is allowed for portable/community
    installations. If an explicit environment path is supplied,
    that policy is required and configuration errors propagate.
    """

    import os

    from atlas.services.sentinel.expected_state import (
        ExpectedAssetStateSource,
        load_expected_state_policy,
    )


    explicit_path = (
        os.environ.get(
            "ATLAS_SENTINEL_EXPECTATIONS_PATH"
        )
    )


    policy = None


    if explicit_path:
        policy = (
            load_expected_state_policy(
                explicit_path
            )
        )

    else:
        try:
            policy = (
                load_expected_state_policy()
            )

        except FileNotFoundError:
            policy = None


    managed_asset_ids = (
        policy.asset_ids
        if policy is not None
        else frozenset()
    )


    repository = AssetRepository()


    sources = [
        StorageHealthSource(
            repository=repository
        ),
    ]


    if policy is not None:
        sources.append(
            ExpectedAssetStateSource(
                repository=repository,
                policy=policy,
            )
        )


    sources.append(
        CriticalAssetStateSource(
            repository=repository,
            excluded_asset_ids=(
                managed_asset_ids
            ),
        )
    )


    return tuple(
        sources
    )

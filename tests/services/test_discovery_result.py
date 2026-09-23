from atlas.models.discovery import (
    DiscoveryResult,
)


def test_discovery_result_defaults_to_authoritative():

    result = DiscoveryResult()

    assert result.complete is True
    assert result.errors == []


def test_discovery_result_can_report_degraded_discovery():

    result = DiscoveryResult(
        complete=False,
        errors=[
            "Proxmox unavailable",
        ],
    )

    assert result.complete is False

    assert result.errors == [
        "Proxmox unavailable",
    ]

import json

from atlas.services.sky.discovery import (
    SkyDiscoveryService,
)


def test_reception_scoring_prefers_current_vhf_dipole():
    score, level, _ = (
        SkyDiscoveryService._reception_score(
            137_800_000
        )
    )

    assert score == 100
    assert level == "MUY FAVORABLE"

    uhf_score, uhf_level, _ = (
        SkyDiscoveryService._reception_score(
            437_800_000
        )
    )

    assert uhf_score == 65
    assert uhf_level == "POSIBLE"


def test_normalizes_active_satnogs_transmitter():
    satellites = {
        "ABC": {
            "name": "SAT PRUEBA",
            "norad_cat_id": 12345,
        }
    }

    result = (
        SkyDiscoveryService
        ._normalize_transmitter(
            {
                "uuid": "tx-1",
                "satellite": "ABC",
                "status": "active",
                "unconfirmed": False,
                "downlink_low": 145_900_000,
                "mode": "BPSK",
                "baud": 1200,
                "description": "Telemetría",
            },
            satellites,
        )
    )

    assert result is not None
    assert (
        result["satellite_name"]
        == "SAT PRUEBA"
    )
    assert result["norad_id"] == 12345
    assert result["downlink_mhz"] == 145.9
    assert (
        result["current_antenna_candidate"]
        is True
    )


def test_ignores_unconfirmed_or_inactive_transmitter():
    assert (
        SkyDiscoveryService
        ._normalize_transmitter(
            {
                "status": "inactive",
                "downlink_low": 137_800_000,
            },
            {},
        )
        is None
    )

    assert (
        SkyDiscoveryService
        ._normalize_transmitter(
            {
                "status": "active",
                "unconfirmed": True,
                "downlink_low": 137_800_000,
            },
            {},
        )
        is None
    )


def test_cache_is_local_and_offline(tmp_path):
    path = (
        tmp_path
        / "catalog.json"
    )

    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-10-11T00:00:00+00:00",
                "source": "SatNOGS DB",
                "targets": [
                    {
                        "satellite_name": "A",
                        "downlink_mhz": 137.5,
                    }
                ],
            }
        )
    )

    payload = (
        SkyDiscoveryService(
            path
        ).load_cache()
    )

    assert len(
        payload["targets"]
    ) == 1

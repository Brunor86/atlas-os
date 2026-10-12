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
            "status": "alive",
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

    assert (
        result["priority_score"]
        > result["reception_score"]
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


def test_rejects_transmitter_marked_not_alive():
    satellites = {
        "12345": {
            "name": "SAT",
            "norad_cat_id": 12345,
            "status": "alive",
        }
    }

    assert (
        SkyDiscoveryService
        ._normalize_transmitter(
            {
                "status": "active",
                "alive": False,
                "unconfirmed": False,
                "norad_cat_id": 12345,
                "downlink_low": 145_900_000,
                "mode": "BPSK",
            },
            satellites,
        )
        is None
    )


def test_rejects_transmitter_without_alive_spacecraft():
    satellites = {
        "12345": {
            "name": "SAT",
            "norad_cat_id": 12345,
            "status": "dead",
        }
    }

    assert (
        SkyDiscoveryService
        ._normalize_transmitter(
            {
                "status": "active",
                "alive": True,
                "unconfirmed": False,
                "norad_cat_id": 12345,
                "downlink_low": 145_900_000,
                "mode": "BPSK",
            },
            satellites,
        )
        is None
    )


def test_priority_rewards_decodable_modes_and_science():
    interesting = (
        SkyDiscoveryService._priority_score(
            reception_score=100,
            mode="GMSK",
            service="Space Research",
            baud=4800,
        )
    )

    unknown = (
        SkyDiscoveryService._priority_score(
            reception_score=100,
            mode="UNKNOWN",
            service="Unknown",
            baud=None,
        )
    )

    assert interesting > unknown


def test_accepts_current_satnogs_in_orbit_status():
    satellites = {
        "SAT-ID": {
            "name": "SAT ACTIVO",
            "norad_cat_id": 54321,
            "status": "in orbit",
        }
    }

    result = (
        SkyDiscoveryService
        ._normalize_transmitter(
            {
                "uuid": "tx-live",
                "satellite": "SAT-ID",
                "status": "active",
                "alive": True,
                "unconfirmed": False,
                "downlink_low": 145_825_000,
                "mode": "AFSK",
                "baud": 1200,
                "service": "Amateur",
            },
            satellites,
        )
    )

    assert result is not None
    assert result["norad_id"] == 54321
    assert result["current_antenna_candidate"] is True

import json

from atlas.services.sky.opportunities import (
    SkyOpportunityService,
    _expected_product,
    _pass_bonus,
)


def test_expected_product_classification():
    assert (
        _expected_product(
            "LRPT",
            "weather",
        )
        == "Imagen meteorológica"
    )

    assert (
        _expected_product(
            "SSTV",
            "imaging",
        )
        == "Imagen SSTV"
    )

    assert (
        _expected_product(
            "AFSK",
            "AX.25 APRS",
        )
        == "Paquetes AX.25 / APRS"
    )


def test_pass_bonus_rewards_elevation_and_science_product():
    high_image = _pass_bonus(
        max_elevation_deg=60,
        product="Imagen meteorológica",
    )

    low_generic = _pass_bonus(
        max_elevation_deg=16,
        product="Señal RF + firma Doppler",
    )

    assert high_image > low_generic


def test_best_transmitters_deduplicates_spacecraft():
    targets = [
        {
            "satellite_name": "SAT-A",
            "norad_id": 1,
            "current_antenna_candidate": True,
            "priority_score": 100,
        },
        {
            "satellite_name": "SAT-A",
            "norad_id": 1,
            "current_antenna_candidate": True,
            "priority_score": 120,
        },
        {
            "satellite_name": "SAT-B",
            "norad_id": 2,
            "current_antenna_candidate": False,
            "priority_score": 150,
        },
    ]

    selected = (
        SkyOpportunityService
        ._best_transmitters(
            targets,
            max_spacecraft=10,
        )
    )

    assert len(selected) == 1
    assert selected[0]["norad_id"] == 1
    assert selected[0]["priority_score"] == 120


def test_diversify_limits_repeated_passes():
    opportunities = [
        {
            "norad_id": 1,
            "opportunity_score": 150,
            "aos_utc": "a",
        },
        {
            "norad_id": 1,
            "opportunity_score": 140,
            "aos_utc": "b",
        },
        {
            "norad_id": 1,
            "opportunity_score": 130,
            "aos_utc": "c",
        },
        {
            "norad_id": 2,
            "opportunity_score": 120,
            "aos_utc": "d",
        },
    ]

    selected = (
        SkyOpportunityService
        ._diversify(
            opportunities,
            max_results=10,
        )
    )

    assert len(selected) == 3
    assert (
        sum(
            1
            for item in selected
            if item["norad_id"] == 1
        )
        == 2
    )


def test_load_is_offline_cache(tmp_path):
    path = tmp_path / "opportunities.json"

    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-10-12T00:00:00+00:00",
                "opportunities": [
                    {
                        "satellite_name": "SAT-A",
                        "norad_id": 1,
                    }
                ],
            }
        )
    )

    service = SkyOpportunityService(
        catalog_path=tmp_path / "catalog.json",
        output_path=path,
    )

    payload = service.load()

    assert len(
        payload["opportunities"]
    ) == 1

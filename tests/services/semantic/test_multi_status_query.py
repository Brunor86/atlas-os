from atlas.services.semantic.query import (
    SemanticQueryEngine,
)


def engine_without_init():
    return object.__new__(
        SemanticQueryEngine
    )


def test_assets_noun_does_not_mean_online():

    engine = engine_without_init()

    statuses = engine._detect_statuses(
        engine._normalize(
            "¿Qué activos están OFFLINE o DEGRADED?"
        )
    )

    assert statuses == [
        "OFFLINE",
        "DEGRADED",
    ]


def test_contextual_activos_still_means_online():

    engine = engine_without_init()

    statuses = engine._detect_statuses(
        engine._normalize(
            "¿Qué servicios están activos?"
        )
    )

    assert statuses == [
        "ONLINE",
    ]


def test_status_detector_returns_none_for_or_query():

    engine = engine_without_init()

    status = engine._detect_status(
        engine._normalize(
            "¿Qué activos están OFFLINE o DEGRADED?"
        )
    )

    assert status is None


class FakeAPI:

    def assets(
        self,
        *,
        status=None,
        asset_type=None,
        role=None,
    ):

        rows = {
            "OFFLINE": [
                {
                    "id": "asset-offline",
                    "name": "offline",
                    "status": "OFFLINE",
                },
            ],
            "DEGRADED": [
                {
                    "id": "asset-degraded",
                    "name": "degraded",
                    "status": "DEGRADED",
                },
            ],
        }

        return {
            "status": "SUCCESS",
            "assets": rows.get(
                status,
                [],
            ),
        }


def test_multi_status_inventory_is_union():

    engine = engine_without_init()
    engine.api = FakeAPI()

    result = engine._assets_for_statuses(
        [
            "OFFLINE",
            "DEGRADED",
        ]
    )

    assert result["status"] == "SUCCESS"
    assert result["count"] == 2

    assert {
        asset["status"]
        for asset in result["assets"]
    } == {
        "OFFLINE",
        "DEGRADED",
    }

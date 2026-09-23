from types import SimpleNamespace

from atlas.services.intelligence.recommendation.service import (
    ActionRecommendationService,
)
from atlas.services.intelligence.safety.service import (
    ActionSafetyService,
)


class FakeAssetRepository:

    def __init__(
        self,
        assets=None,
    ):
        self.assets = dict(
            assets
            or {}
        )

    def get_asset(
        self,
        asset_id,
    ):
        return self.assets.get(
            asset_id
        )


def docker_asset():

    return SimpleNamespace(
        id=(
            "application-docker-"
            "nginx-proxy-manager"
        ),
        name="nginx-proxy-manager",
        metadata={
            "container_name":
                "nginx-proxy-manager",
        },
        identity=SimpleNamespace(
            serial="f88d76e80ccc",
        ),
    )


def reasoning():

    return {
        "recommended_actions": [
            {
                "action":
                    "restart container",

                "asset_id":
                    (
                        "application-docker-"
                        "nginx-proxy-manager"
                    ),

                "reason":
                    (
                        "nginx-proxy-manager "
                        "container is stopped"
                    ),

                "risk":
                    "MEDIUM",
            },
        ],
    }


def test_recommendation_resolves_docker_asset_to_container_name():

    assets = FakeAssetRepository(
        {
            (
                "application-docker-"
                "nginx-proxy-manager"
            ):
                docker_asset(),
        }
    )

    service = ActionRecommendationService(
        repository=None,
        asset_repository=assets,
    )

    plan = service.recommend_from_reasoning(
        reasoning(),
        incident_id="INC-0002",
    )

    assert plan.action == (
        "restart container"
    )

    assert plan.target == (
        "nginx-proxy-manager"
    )

    assert plan.incident_id == (
        "INC-0002"
    )


def test_safety_prefers_specific_recommendation_target():

    assets = FakeAssetRepository(
        {
            (
                "application-docker-"
                "nginx-proxy-manager"
            ):
                docker_asset(),
        }
    )

    recommendation = (
        ActionRecommendationService(
            repository=None,
            asset_repository=assets,
        )
        .recommend_from_reasoning(
            reasoning(),
            incident_id="INC-0002",
        )
    )

    incident = SimpleNamespace(
        asset="docker-service",
        incident_id="INC-0002",
        recommendation=recommendation,
        diagnosis={},
    )

    result = (
        ActionSafetyService()
        .evaluate(
            incident
        )
    )

    assert result[
        "action"
    ] == "restart container"

    assert result[
        "target"
    ] == "nginx-proxy-manager"

    assert result[
        "rollback"
    ] == (
        "docker start "
        "nginx-proxy-manager"
    )

    assert result[
        "status"
    ] == "PENDING_APPROVAL"


def test_unresolved_asset_keeps_specific_asset_id():

    service = ActionRecommendationService(
        repository=None,
        asset_repository=(
            FakeAssetRepository()
        ),
    )

    plan = (
        service
        .recommend_from_reasoning(
            reasoning(),
            incident_id="INC-0002",
        )
    )

    assert plan.target == (
        "application-docker-"
        "nginx-proxy-manager"
    )

    assert plan.target != (
        "infrastructure"
    )


def test_explicit_target_remains_authoritative():

    service = ActionRecommendationService(
        repository=None,
        asset_repository=(
            FakeAssetRepository()
        ),
    )

    data = reasoning()

    data[
        "recommended_actions"
    ][0][
        "target"
    ] = "explicit-container"

    plan = (
        service
        .recommend_from_reasoning(
            data,
            incident_id="INC-0002",
        )
    )

    assert plan.target == (
        "explicit-container"
    )


def test_specific_reasoning_action_refines_generic_for_same_asset():

    assets = FakeAssetRepository(
        {
            (
                "application-docker-"
                "nginx-proxy-manager"
            ):
                docker_asset(),
        }
    )

    service = ActionRecommendationService(
        repository=None,
        asset_repository=assets,
    )

    reasoning = {
        "recommended_actions": [
            {
                "action":
                    "restart asset",

                "asset_id":
                    "application-docker-nginx-proxy-manager",

                "reason":
                    "asset is offline",

                "risk":
                    "MEDIUM",
            },
            {
                "action":
                    "restart container",

                "asset_id":
                    "application-docker-nginx-proxy-manager",

                "reason":
                    "container is stopped",

                "risk":
                    "MEDIUM",
            },
        ]
    }

    plan = service.recommend_from_reasoning(
        reasoning,
        incident_id="INC-0002",
    )

    assert plan.action == (
        "restart container"
    )

    assert plan.target == (
        "nginx-proxy-manager"
    )

    assert plan.reason == [
        "container is stopped"
    ]


def test_generic_action_is_kept_without_specific_alternative():

    service = ActionRecommendationService(
        repository=None,
        asset_repository=FakeAssetRepository(),
    )

    reasoning = {
        "recommended_actions": [
            {
                "action":
                    "restart asset",

                "asset_id":
                    "application-docker-nginx-proxy-manager",

                "reason":
                    "asset is offline",

                "risk":
                    "MEDIUM",
            },
        ]
    }

    plan = service.recommend_from_reasoning(
        reasoning,
        incident_id="INC-0002",
    )

    assert plan.action == (
        "restart asset"
    )


def test_specific_action_for_other_asset_does_not_override_generic():

    service = ActionRecommendationService(
        repository=None,
        asset_repository=FakeAssetRepository(),
    )

    reasoning = {
        "recommended_actions": [
            {
                "action":
                    "restart asset",

                "asset_id":
                    "application-docker-nginx-proxy-manager",

                "reason":
                    "asset is offline",

                "risk":
                    "MEDIUM",
            },
            {
                "action":
                    "restart container",

                "asset_id":
                    "application-docker-flaresolverr",

                "reason":
                    "other container stopped",

                "risk":
                    "MEDIUM",
            },
        ]
    }

    plan = service.recommend_from_reasoning(
        reasoning,
        incident_id="INC-0002",
    )

    assert plan.action == (
        "restart asset"
    )

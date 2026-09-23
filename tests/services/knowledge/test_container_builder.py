from types import SimpleNamespace

from atlas.core.asset import (
    AssetRole,
    Criticality,
)
from atlas.core.relationship import (
    RelationshipType,
)

from atlas.services.knowledge.builders.container import (
    ContainerBuilder,
)


class FakeRegistry:

    def __init__(
        self,
        assets,
    ):

        self.assets = {
            asset.id: asset
            for asset in assets
        }

    def get_asset(
        self,
        asset_id,
    ):

        return self.assets.get(
            asset_id
        )


def test_container_builder_uses_asset_metadata_and_relationships():

    dependency = SimpleNamespace(
        id="application-docker-database",
        name="database-workload",
    )

    relationship = SimpleNamespace(
        type=RelationshipType.DEPENDS_ON,
        target=dependency.id,
    )

    asset = SimpleNamespace(
        id="application-docker-web",
        name="web-workload",
        type=None,
        metadata={
            "runtime":
                "docker",

            "image":
                "example/web:latest",

            "compose_project":
                "sample-stack",

            "compose_service":
                "web",

            "labels": {
                "org.opencontainers.image.title":
                    "Example Web Service",
            },
        },
        criticality=Criticality.HIGH,
        asset_roles={
            AssetRole.APPLICATION_SERVER,
        },
        relationships=[
            relationship,
        ],
    )

    card = SimpleNamespace(
        summary="",
        roles=[],
        observations=[],
        application_dependencies=[],
    )

    graph = SimpleNamespace(
        topology=SimpleNamespace(
            assets=FakeRegistry(
                [
                    dependency,
                ]
            )
        ),
        resolver=None,
    )

    result = ContainerBuilder().build(
        asset,
        card,
        graph,
    )

    assert (
        result.summary
        == "Example Web Service running as application container."
    )

    assert (
        "APPLICATION_SERVER"
        in result.roles
    )

    assert (
        "Runtime: docker"
        in result.observations
    )

    assert (
        "Image: example/web:latest"
        in result.observations
    )

    assert (
        "Criticality: HIGH"
        in result.observations
    )

    assert (
        result.application_dependencies
        == [
            "database-workload",
        ]
    )


def test_container_builder_does_not_invent_dependencies():

    asset = SimpleNamespace(
        id="application-docker-generic",
        name="generic-workload",
        metadata={
            "runtime":
                "docker",
        },
        criticality=Criticality.MEDIUM,
        asset_roles=set(),
        relationships=[],
    )

    card = SimpleNamespace(
        summary="",
        roles=[],
        observations=[],
        application_dependencies=[],
    )

    graph = SimpleNamespace(
        topology=None,
        resolver=None,
    )

    result = ContainerBuilder().build(
        asset,
        card,
        graph,
    )

    assert (
        result.application_dependencies
        == []
    )

    assert (
        result.roles
        == [
            "APPLICATION_CONTAINER",
        ]
    )

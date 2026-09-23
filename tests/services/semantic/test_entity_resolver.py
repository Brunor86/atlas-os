from atlas.core.asset import (
    Asset,
    AssetType,
)

from atlas.core.semantic import (
    SemanticEntityKind,
)

from atlas.services.assets.registry import (
    AssetRegistry,
)

from atlas.services.semantic.entity_resolver import (
    SemanticEntityResolver,
)


def make_asset(
    asset_id,
    name,
    *,
    group=None,
    scope="host-a",
):

    metadata = {}

    if group is not None:

        metadata[
            "semantic_groups"
        ] = [
            {
                "kind":
                    "application_stack",

                "value":
                    group,

                "scope":
                    scope,

                "source":
                    "synthetic_provider",

                "confidence":
                    0.99,
            }
        ]

    return Asset(
        id=asset_id,
        name=name,
        type=AssetType.APPLICATION,
        metadata=metadata,
    )


def test_resolves_arbitrary_discovered_group():

    registry = AssetRegistry()

    registry.register(
        make_asset(
            "app-nebula-api",
            "nebula-api",
            group="nebula",
        )
    )

    registry.register(
        make_asset(
            "app-nebula-db",
            "database-random-name",
            group="nebula",
        )
    )

    resolver = SemanticEntityResolver(
        registry
    )

    result = resolver.resolve(
        "nebula"
    )

    assert (
        result.kind
        == SemanticEntityKind.GROUP
    )

    assert set(
        result.member_ids
    ) == {
        "app-nebula-api",
        "app-nebula-db",
    }

    assert (
        result.group_kind
        == "application_stack"
    )

    assert (
        result.group_scope
        == "host-a"
    )


def test_group_beats_partial_asset_name():

    registry = AssetRegistry()

    registry.register(
        make_asset(
            "partial-first",
            "orion-worker",
        )
    )

    registry.register(
        make_asset(
            "group-api",
            "totally-unrelated-api",
            group="orion",
        )
    )

    registry.register(
        make_asset(
            "group-db",
            "totally-unrelated-db",
            group="orion",
        )
    )

    resolver = SemanticEntityResolver(
        registry
    )

    result = resolver.resolve(
        "orion"
    )

    assert (
        result.kind
        == SemanticEntityKind.GROUP
    )

    assert set(
        result.member_ids
    ) == {
        "group-api",
        "group-db",
    }


def test_exact_asset_name_beats_group():

    registry = AssetRegistry()

    registry.register(
        make_asset(
            "exact",
            "cosmos",
        )
    )

    registry.register(
        make_asset(
            "member",
            "cosmos-worker",
            group="cosmos",
        )
    )

    resolver = SemanticEntityResolver(
        registry
    )

    result = resolver.resolve(
        "cosmos"
    )

    assert (
        result.kind
        == SemanticEntityKind.ASSET
    )

    assert result.asset_id == "exact"


def test_same_group_name_in_two_scopes_is_ambiguous():

    registry = AssetRegistry()

    registry.register(
        make_asset(
            "stack-host-a",
            "worker-a",
            group="atlas-stack",
            scope="host-a",
        )
    )

    registry.register(
        make_asset(
            "stack-host-b",
            "worker-b",
            group="atlas-stack",
            scope="host-b",
        )
    )

    resolver = SemanticEntityResolver(
        registry
    )

    result = resolver.resolve(
        "atlas-stack"
    )

    assert (
        result.kind
        == SemanticEntityKind.AMBIGUOUS
    )

    assert len(
        result.candidates
    ) == 2


def test_unknown_entity_is_not_found():

    registry = AssetRegistry()

    resolver = SemanticEntityResolver(
        registry
    )

    result = resolver.resolve(
        "something-that-does-not-exist"
    )

    assert (
        result.kind
        == SemanticEntityKind.NOT_FOUND
    )


def test_canonical_group_reference_round_trips():

    registry = AssetRegistry()

    registry.register(
        make_asset(
            "app-nebula-api",
            "nebula-api",
            group="nebula",
        )
    )

    registry.register(
        make_asset(
            "app-nebula-db",
            "nebula-db",
            group="nebula",
        )
    )

    resolver = SemanticEntityResolver(
        registry
    )

    first = resolver.resolve(
        "nebula"
    )

    assert (
        first.kind
        == SemanticEntityKind.GROUP
    )

    reference = first.reference

    assert reference is not None

    second = resolver.resolve(
        reference
    )

    assert (
        second.kind
        == SemanticEntityKind.GROUP
    )

    assert second.reference == reference

    assert set(
        second.member_ids
    ) == set(
        first.member_ids
    )

    assert (
        second.group_kind
        == first.group_kind
    )

    assert (
        second.group_value
        == first.group_value
    )

    assert (
        second.group_scope
        == first.group_scope
    )

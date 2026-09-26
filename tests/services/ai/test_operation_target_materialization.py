from types import SimpleNamespace

from atlas.services.ai.operator.planning import (
    OperationPlan,
)

from atlas.services.ai.service import (
    _materialize_operation_plan,
)


class FakeResolver:

    def __init__(
        self,
        resolution,
    ):
        self.resolution = resolution
        self.calls = []


    def resolve(
        self,
        query,
        *,
        requested_resource_type=None,
    ):

        self.calls.append(
            {
                "query": query,
                "requested_resource_type":
                    requested_resource_type,
            }
        )

        return self.resolution


class ExplodingResolver:

    def resolve(
        self,
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "resolver must not run for NONE intent"
        )


def resolution(
    *,
    status="RESOLVED",
    query="olivasat",
    resource_type="lxc",
    target="103",
    asset_id="lxc-103",
    asset_name="olivasat",
    reason="resolved",
    candidates=(),
):
    return SimpleNamespace(
        status=status,
        query=query,
        resource_type=resource_type,
        target=target,
        asset_id=asset_id,
        asset_name=asset_name,
        reason=reason,
        candidates=candidates,
    )


def test_named_asset_is_materialized_to_canonical_lxc():

    plan = OperationPlan(
        intent="PROPOSE",
        resource_type=None,
        action="restart",
        target="olivasat",
        reason="explicit restart request",
        confidence=0.99,
    )

    fake = FakeResolver(
        resolution()
    )

    result = (
        _materialize_operation_plan(
            plan,
            resolver=fake,
        )
    )

    assert result["status"] == "RESOLVED"
    assert result["requested_target"] == "olivasat"
    assert result["resource_type"] == "lxc"
    assert result["target"] == "103"
    assert result["asset_name"] == "olivasat"

    assert fake.calls == [
        {
            "query": "olivasat",
            "requested_resource_type": None,
        }
    ]


def test_explicit_resource_type_is_preserved_for_resolution():

    plan = OperationPlan(
        intent="PROPOSE",
        resource_type="vm",
        action="start",
        target="300",
        reason="explicit VM start request",
        confidence=0.99,
    )

    fake = FakeResolver(
        resolution(
            query="300",
            resource_type="vm",
            target="300",
            asset_id="vm-300",
            asset_name="atlas-windows",
        )
    )

    result = (
        _materialize_operation_plan(
            plan,
            resolver=fake,
        )
    )

    assert result["status"] == "RESOLVED"
    assert result["resource_type"] == "vm"
    assert result["target"] == "300"

    assert fake.calls == [
        {
            "query": "300",
            "requested_resource_type": "vm",
        }
    ]


def test_unresolved_named_target_fails_closed():

    plan = OperationPlan(
        intent="PROPOSE",
        resource_type=None,
        action="stop",
        target="unknown-host",
        reason="explicit stop request",
        confidence=0.99,
    )

    fake = FakeResolver(
        resolution(
            status="NOT_FOUND",
            query="unknown-host",
            resource_type=None,
            target=None,
            asset_id=None,
            asset_name=None,
            reason=(
                "no active executable asset "
                "matches target"
            ),
        )
    )

    result = (
        _materialize_operation_plan(
            plan,
            resolver=fake,
        )
    )

    assert result["status"] == "NOT_FOUND"
    assert result["target"] is None
    assert result["resource_type"] is None


def test_non_operational_plan_never_queries_resolver():

    plan = OperationPlan(
        intent="NONE",
        resource_type=None,
        action=None,
        target=None,
        reason="informational request",
        confidence=1.0,
    )

    result = (
        _materialize_operation_plan(
            plan,
            resolver=ExplodingResolver(),
        )
    )

    assert result["status"] == "NOT_APPLICABLE"
    assert result["target"] is None
    assert result["resource_type"] is None

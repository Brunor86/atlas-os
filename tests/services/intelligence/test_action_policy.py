from atlas.core.asset import (
    Asset,
    AssetPresence,
    AssetType,
    Capability,
    Criticality,
    ServiceImportance,
)

from atlas.models.action import SafeAction

from atlas.services.intelligence.policy.service import (
    ActionPolicyService,
)


def make_asset(
    *,
    criticality=Criticality.MEDIUM,
    importance=ServiceImportance.NORMAL,
    capabilities=None,
    presence=AssetPresence.ACTIVE,
):

    return Asset(
        id="asset-test",
        name="test-container",
        type=AssetType.APPLICATION,
        criticality=criticality,
        service_importance=importance,
        capabilities=set(
            capabilities
            or []
        ),
        presence=presence,
    )


def make_action(
    action,
):

    return SafeAction(
        action=action,
        target="test-container",
    )


def test_unknown_target_is_blocked():

    policy = ActionPolicyService()

    result = policy.evaluate(
        make_action(
            "restart container"
        ),
        None,
    )

    assert result["status"] == "BLOCKED"

    assert (
        "not registered"
        in result["reason"]
    )


def test_missing_capability_is_blocked():

    policy = ActionPolicyService()

    asset = make_asset(
        capabilities={
            Capability.START,
        }
    )

    result = policy.evaluate(
        make_action(
            "restart container"
        ),
        asset,
    )

    assert result["status"] == "BLOCKED"

    assert (
        result[
            "required_capability"
        ]
        == "RESTART"
    )


def test_medium_restart_is_allowed():

    policy = ActionPolicyService()

    asset = make_asset(
        criticality=Criticality.MEDIUM,
        importance=ServiceImportance.NORMAL,
        capabilities={
            Capability.RESTART,
        },
    )

    result = policy.evaluate(
        make_action(
            "restart container"
        ),
        asset,
    )

    assert result["status"] == "ALLOWED"


def test_high_restart_is_blocked():

    policy = ActionPolicyService()

    asset = make_asset(
        criticality=Criticality.HIGH,
        importance=ServiceImportance.NORMAL,
        capabilities={
            Capability.RESTART,
        },
    )

    result = policy.evaluate(
        make_action(
            "restart container"
        ),
        asset,
    )

    assert result["status"] == "BLOCKED"


def test_important_restart_is_blocked():

    policy = ActionPolicyService()

    asset = make_asset(
        criticality=Criticality.MEDIUM,
        importance=ServiceImportance.IMPORTANT,
        capabilities={
            Capability.RESTART,
        },
    )

    result = policy.evaluate(
        make_action(
            "restart container"
        ),
        asset,
    )

    assert result["status"] == "BLOCKED"


def test_critical_stop_is_blocked():

    policy = ActionPolicyService()

    asset = make_asset(
        criticality=Criticality.CRITICAL,
        capabilities={
            Capability.STOP,
        },
    )

    result = policy.evaluate(
        make_action(
            "stop container"
        ),
        asset,
    )

    assert result["status"] == "BLOCKED"


def test_critical_start_is_allowed():

    policy = ActionPolicyService()

    asset = make_asset(
        criticality=Criticality.CRITICAL,
        importance=ServiceImportance.CRITICAL,
        capabilities={
            Capability.START,
        },
    )

    result = policy.evaluate(
        make_action(
            "start container"
        ),
        asset,
    )

    assert result["status"] == "ALLOWED"


def test_unknown_action_is_blocked():

    policy = ActionPolicyService()

    asset = make_asset(
        capabilities={
            Capability.START,
            Capability.STOP,
            Capability.RESTART,
        }
    )

    result = policy.evaluate(
        make_action(
            "delete container"
        ),
        asset,
    )

    assert result["status"] == "BLOCKED"


def test_system_importance_is_neutral_for_medium_restart():

    policy = ActionPolicyService()

    asset = make_asset(
        criticality=Criticality.MEDIUM,
        importance=ServiceImportance.SYSTEM,
        capabilities={
            Capability.RESTART,
        },
    )

    result = policy.evaluate(
        make_action(
            "restart container"
        ),
        asset,
    )

    assert result["status"] == "ALLOWED"



def test_stale_asset_is_blocked():

    policy = ActionPolicyService()

    asset = make_asset(
        capabilities={
            Capability.START,
        },
        presence=AssetPresence.STALE,
    )

    result = policy.evaluate(
        make_action(
            "start container"
        ),
        asset,
    )

    assert result["status"] == "BLOCKED"

    assert result[
        "presence"
    ] == "STALE"

    assert (
        "not active"
        in result["reason"]
    )


def test_retired_asset_is_blocked():

    policy = ActionPolicyService()

    asset = make_asset(
        capabilities={
            Capability.START,
        },
        presence=AssetPresence.RETIRED,
    )

    result = policy.evaluate(
        make_action(
            "start container"
        ),
        asset,
    )

    assert result["status"] == "BLOCKED"

    assert result[
        "presence"
    ] == "RETIRED"

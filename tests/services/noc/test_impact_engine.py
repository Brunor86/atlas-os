from types import SimpleNamespace

from atlas.services.noc.impact import ImpactEngine


def make_asset(
    asset_id="app-1",
    name="NPM",
    criticality="MEDIUM",
    roles=None,
):
    return SimpleNamespace(
        id=asset_id,
        name=name,
        criticality=SimpleNamespace(
            name=criticality,
        ),
        asset_roles=[
            SimpleNamespace(name=role)
            for role in (roles or [])
        ],
    )


def make_engine(
    asset,
    upstream=None,
    downstream=None,
):
    engine = object.__new__(
        ImpactEngine
    )

    engine.assets = SimpleNamespace(
        get_asset=lambda asset_id: asset,
    )

    engine.topology = SimpleNamespace(
        critical_upstream=lambda asset_id: (
            upstream or []
        ),
        downstream=lambda asset_id: (
            downstream or []
        ),
    )

    return engine


def test_upstream_does_not_inflate_incident_impact():

    asset = make_asset(
        criticality="MEDIUM",
    )

    upstream = [
        {
            "asset_id": "vm-100",
            "relationship": "HOSTED_ON",
            "depth": 1,
            "confidence": 1.0,
            "relationship_weight": 10,
            "impact_score": 10.0,
            "evidence": [],
        },
        {
            "asset_id": "proxmox-1",
            "relationship": "HOSTED_ON",
            "depth": 2,
            "confidence": 1.0,
            "relationship_weight": 10,
            "impact_score": 5.0,
            "evidence": [],
        },
    ]

    engine = make_engine(
        asset,
        upstream=upstream,
        downstream=[],
    )

    result = engine.analyze(
        "app-1"
    )

    assert result["impact_score"] == 30

    assert result["severity"] == "MEDIUM"

    assert (
        result["operational_upstream"]
        == upstream
    )

    assert (
        result["root_causes"][0]["asset_id"]
        == "vm-100"
    )


def test_downstream_increases_incident_impact():

    asset = make_asset(
        criticality="MEDIUM",
    )

    downstream = [
        {
            "asset_id": "app-2",
        },
        {
            "asset_id": "app-3",
        },
        {
            "asset_id": "app-4",
        },
    ]

    engine = make_engine(
        asset,
        upstream=[],
        downstream=downstream,
    )

    result = engine.analyze(
        "app-1"
    )

    assert result["impact_score"] == 60

    assert result["severity"] == "HIGH"

    assert len(
        result["downstream"]
    ) == 3


def test_critical_asset_with_role_can_be_critical():

    asset = make_asset(
        criticality="CRITICAL",
        roles=[
            "DATABASE_SERVER",
        ],
    )

    engine = make_engine(
        asset,
        upstream=[],
        downstream=[],
    )

    result = engine.analyze(
        "db-1"
    )

    assert result["impact_score"] == 140

    assert result["severity"] == "CRITICAL"

    assert (
        result["criticality"]
        == "CRITICAL"
    )

    assert (
        "DATABASE_SERVER"
        in result["roles"]
    )

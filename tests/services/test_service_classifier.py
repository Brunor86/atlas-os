from types import SimpleNamespace

from atlas.core.asset import (
    Criticality,
    ServiceImportance,
    ServiceRole,
)

from atlas.services.assets.builder import (
    AssetBuilder,
)

from atlas.services.assets.service_classifier import (
    ServiceClassifier,
)


def test_database_role_does_not_imply_importance():

    result = ServiceClassifier().classify(
        "postgresql.service"
    )

    assert (
        result.role
        == ServiceRole.DATABASE
    )

    assert (
        result.importance
        == ServiceImportance.SYSTEM
    )


def test_container_runtime_role_does_not_imply_importance():

    result = ServiceClassifier().classify(
        "docker.service"
    )

    assert (
        result.role
        == ServiceRole.CONTAINER_RUNTIME
    )

    assert (
        result.importance
        == ServiceImportance.SYSTEM
    )


def test_monitoring_role_does_not_imply_importance():

    result = ServiceClassifier().classify(
        "metrics-exporter.service"
    )

    assert (
        result.role
        == ServiceRole.MONITORING
    )

    assert (
        result.importance
        == ServiceImportance.SYSTEM
    )


def test_explicit_string_metadata_is_resolved():

    result = ServiceClassifier().classify(
        "opaque.service",
        {
            "service_role":
                "database",
            "importance":
                "critical",
        },
    )

    assert (
        result.role
        == ServiceRole.DATABASE
    )

    assert (
        result.importance
        == ServiceImportance.CRITICAL
    )


def test_explicit_enum_metadata_is_resolved():

    result = ServiceClassifier().classify(
        "opaque.service",
        {
            "service_role":
                ServiceRole.SECURITY,
            "importance":
                ServiceImportance.IMPORTANT,
        },
    )

    assert (
        result.role
        == ServiceRole.SECURITY
    )

    assert (
        result.importance
        == ServiceImportance.IMPORTANT
    )


def test_invalid_importance_does_not_guess():

    result = ServiceClassifier().classify(
        "postgresql.service",
        {
            "importance":
                "SUPER_CRITICAL_DATABASE",
        },
    )

    assert (
        result.role
        == ServiceRole.DATABASE
    )

    assert (
        result.importance
        == ServiceImportance.SYSTEM
    )


def test_system_service_builder_uses_neutral_operational_defaults():

    service = SimpleNamespace(
        hostname="generic-host",
        name="postgresql.service",
        status="active",
    )

    asset = (
        AssetBuilder()
        .from_system_service(
            service
        )
    )

    assert (
        asset.service_role
        == ServiceRole.DATABASE
    )

    assert (
        asset.service_importance
        == ServiceImportance.SYSTEM
    )

    assert (
        asset.criticality
        == Criticality.MEDIUM
    )

# ATLAS DEV v0.122 · IMPORTANCE EXPLAINABILITY


def test_explain_importance_reflects_stored_builder_classification():
    from types import SimpleNamespace

    from atlas.services.assets.builder import AssetBuilder

    service = SimpleNamespace(
        hostname="test-host",
        name="docker.service",
        status="active",
    )

    asset = (
        AssetBuilder()
        .from_system_service(
            service
        )
    )

    result = (
        asset.explain_importance()
    )

    assert result == {
        "service_role": (
            asset.service_role.name
            if asset.service_role
            else None
        ),
        "service_importance": (
            asset.service_importance.name
            if asset.service_importance
            else None
        ),
        "reason": (
            asset.metadata.get(
                "classification_reason"
            )
        ),
    }


def test_explain_importance_missing_stored_reason_returns_none():
    from types import SimpleNamespace

    from atlas.services.assets.builder import AssetBuilder

    service = SimpleNamespace(
        hostname="test-host",
        name="docker.service",
        status="active",
    )

    asset = (
        AssetBuilder()
        .from_system_service(
            service
        )
    )

    asset.metadata = dict(
        asset.metadata
    )

    asset.metadata.pop(
        "classification_reason",
        None,
    )

    result = (
        asset.explain_importance()
    )

    assert (
        result["reason"]
        is None
    )


def test_explain_importance_does_not_mutate_asset():
    from types import SimpleNamespace

    from atlas.services.assets.builder import AssetBuilder

    service = SimpleNamespace(
        hostname="test-host",
        name="docker.service",
        status="active",
    )

    asset = (
        AssetBuilder()
        .from_system_service(
            service
        )
    )

    before = (
        asset.service_role,
        asset.service_importance,
        dict(
            asset.metadata
        ),
    )

    asset.explain_importance()

    after = (
        asset.service_role,
        asset.service_importance,
        dict(
            asset.metadata
        ),
    )

    assert after == before

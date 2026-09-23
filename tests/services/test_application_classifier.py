from atlas.core.asset import AssetRole

from atlas.services.assets.application_classifier import (
    ApplicationClassifier,
)


def test_compose_project_does_not_imply_application_role():

    classifier = ApplicationClassifier()

    result = classifier.classify(
        "dashboard",
        {
            "compose_project": "monitoring",
            "compose_service": "dashboard",
            "labels": {},
        },
    )

    assert result.role is None
    assert result.confidence == 0.0


def test_oci_description_can_classify_monitoring_workload():

    classifier = ApplicationClassifier()

    result = classifier.classify(
        "metrics-workload",
        {
            "labels": {
                "org.opencontainers.image.description":
                    "Observability service exposing system metrics",
            },
        },
    )

    assert result.role == AssetRole.MONITORING_NODE
    assert result.confidence > 0.0


def test_bypass_proxy_is_classified_as_utility():

    classifier = ApplicationClassifier()

    result = classifier.classify(
        "challenge-helper",
        {
            "labels": {
                "org.opencontainers.image.description":
                    "Proxy server to bypass web protection",
            },
        },
    )

    assert result.role == AssetRole.UTILITY_SERVICE

from types import SimpleNamespace

from atlas.services.intelligence.execution.validators import (
    ActionValidator,
)
from atlas.services.intelligence.safety.service import (
    ActionSafetyService,
)


def test_start_container_is_allowed_by_execution_policy():

    result = ActionValidator().validate(
        "start container"
    )

    assert result["valid"] is True


def test_start_container_is_low_risk_and_requires_approval():

    incident = SimpleNamespace(
        incident_id="OP-TEST",
        asset="flaresolverr",
        diagnosis={},
        recommendation={
            "action": "start container",
            "incident_id": "OP-TEST",
            "evidence": [
                {
                    "source": "test",
                }
            ],
        },
    )

    result = ActionSafetyService().evaluate(
        incident
    )

    assert result["action"] == "start container"
    assert result["target"] == "flaresolverr"
    assert result["risk"] == "LOW"
    assert result["status"] == "PENDING_APPROVAL"
    assert result["requires_approval"] is True
    assert result["rollback"] == (
        "docker stop flaresolverr"
    )

import pytest
from pydantic import ValidationError

from atlas.services.ai.investigator.planning import (
    InvestigationPlan,
    RelationAnchor,
)
from atlas.services.ai.investigator.pydantic_planner import (
    PydanticInvestigationPlanner,
)
from atlas.services.ai.investigator.scope import (
    EvidenceDomain,
    InvestigationScopeMode,
)


class FakeResult:

    def __init__(
        self,
        output,
    ):
        self.output = output


class FakeAgent:

    def __init__(
        self,
        output,
    ):
        self.output = output
        self.requests = []

    def run_sync(
        self,
        request,
    ):
        self.requests.append(
            request
        )

        return FakeResult(
            self.output
        )


def relation_plan():

    return InvestigationPlan(
        domain=EvidenceDomain.RELATION,
        scope_mode=(
            InvestigationScopeMode.TARGET
        ),
        target_query="photo stack",
        relationship="DEPENDS_ON",
        relation_anchor=(
            RelationAnchor.SUBJECT
        ),
    )


def test_returns_typed_investigation_plan():

    expected = relation_plan()

    agent = FakeAgent(
        expected
    )

    planner = (
        PydanticInvestigationPlanner(
            agent
        )
    )

    result = planner.plan(
        "¿De qué depende photo stack?"
    )

    assert result == expected

    assert agent.requests == [
        "¿De qué depende photo stack?"
    ]


def test_validates_mapping_output():

    expected = relation_plan()

    agent = FakeAgent(
        expected.model_dump(
            mode="json",
            exclude={
                "direction",
            },
        )
    )

    planner = (
        PydanticInvestigationPlanner(
            agent
        )
    )

    result = planner.plan(
        "dependencies of photo stack"
    )

    assert isinstance(
        result,
        InvestigationPlan,
    )

    assert (
        result.domain
        == EvidenceDomain.RELATION
    )

    assert (
        result.relationship
        == "DEPENDS_ON"
    )

    assert (
        result.direction.value
        == "DOWNSTREAM"
    )


def test_mapping_cannot_inject_derived_direction():

    expected = relation_plan()

    payload = expected.model_dump(
        mode="json",
        exclude={
            "direction",
        },
    )

    #
    # direction is derived deterministically by ATLAS
    # from relation_anchor. It is never planner input.
    #
    payload[
        "direction"
    ] = "UPSTREAM"

    planner = (
        PydanticInvestigationPlanner(
            FakeAgent(
                payload
            )
        )
    )

    with pytest.raises(
        ValidationError,
        match="direction",
    ):
        planner.plan(
            "dependencies of photo stack"
        )


def test_blank_question_is_rejected():

    planner = (
        PydanticInvestigationPlanner(
            FakeAgent(
                relation_plan()
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        planner.plan(
            "   "
        )


def test_planner_contains_no_tool_backend():

    planner = (
        PydanticInvestigationPlanner(
            FakeAgent(
                relation_plan()
            )
        )
    )

    assert not hasattr(
        planner,
        "tool_backend",
    )

    assert not hasattr(
        planner,
        "execute_tool",
    )

def test_status_instructions_require_structured_selectors():

    from atlas.services.ai.investigator.pydantic_planner import (
        PLANNER_INSTRUCTIONS,
    )

    normalized = " ".join(
        PLANNER_INSTRUCTIONS.split()
    )

    assert (
        "collection_query field is descriptive only"
        in normalized
    )

    assert (
        "asset_type = APPLICATION"
        in normalized
    )

    assert (
        "status_filter = OFFLINE"
        in normalized
    )

    assert (
        "NEVER a query language"
        in normalized
    )

    assert (
        "*application* WHERE STATUS = 'OFFLINE'"
        in normalized
    )

def test_for_ollama_enforces_non_reasoning_model_settings(
    monkeypatch,
):

    from atlas.services.ai.investigator.pydantic_planner import (
        PydanticInvestigationPlanner,
    )

    captured = {}

    class FakeProvider:

        def __init__(
            self,
            *,
            base_url,
            api_key=None,
        ):

            captured[
                "base_url"
            ] = base_url

            captured[
                "api_key"
            ] = api_key


    class FakeModel:

        def __init__(
            self,
            model_name,
            *,
            provider,
            settings=None,
        ):

            captured[
                "model_name"
            ] = model_name

            captured[
                "provider"
            ] = provider

            captured[
                "settings"
            ] = settings


    class FakeNativeOutput:

        def __init__(
            self,
            output_type,
        ):

            captured[
                "output_type"
            ] = output_type


    class FakeAgent:

        def __init__(
            self,
            model,
            *,
            output_type,
            instructions,
        ):

            captured[
                "model"
            ] = model

            captured[
                "native_output"
            ] = output_type

            captured[
                "instructions"
            ] = instructions


    monkeypatch.setattr(
        "pydantic_ai.Agent",
        FakeAgent,
    )

    monkeypatch.setattr(
        "pydantic_ai.models.ollama.OllamaModel",
        FakeModel,
    )

    monkeypatch.setattr(
        "pydantic_ai.providers.ollama.OllamaProvider",
        FakeProvider,
    )

    monkeypatch.setattr(
        "pydantic_ai.output.NativeOutput",
        FakeNativeOutput,
    )

    planner = (
        PydanticInvestigationPlanner
        .for_ollama(
            model_name="planner-model",
            base_url="http://ollama.invalid/v1",
        )
    )

    assert isinstance(
        planner,
        PydanticInvestigationPlanner,
    )

    settings = captured[
        "settings"
    ]

    assert (
        settings[
            "thinking"
        ]
        is False
    )

    assert (
        settings[
            "temperature"
        ]
        == 0.0
    )

    assert (
        settings[
            "max_tokens"
        ]
        == 256
    )

    assert (
        settings[
            "extra_body"
        ][
            "reasoning_effort"
        ]
        == "none"
    )

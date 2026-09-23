from atlas.services.ai.operator.execution import (
    OperatorExecutionStatus,
)
from atlas.services.ai.operator.operator import (
    AIModelOperator,
)


def test_operator_creates_execution():

    operator = AIModelOperator()

    execution = operator.create_execution(
        "diagnosis",
    )

    assert execution.task == "diagnosis"
    assert execution.execution_id
    assert execution.status == OperatorExecutionStatus.CREATED


def test_operator_updates_execution_status():

    operator = AIModelOperator()

    execution = operator.create_execution(
        "diagnosis",
    )

    operator.update_execution(
        execution,
        OperatorExecutionStatus.SELECTING_MODEL,
    )

    assert execution.status == (
        OperatorExecutionStatus.SELECTING_MODEL
    )


def test_operator_records_selected_model():

    operator = AIModelOperator()

    execution = operator.create_execution(
        "diagnosis",
    )

    model = operator.list_models()[0]

    operator.update_execution(
        execution,
        OperatorExecutionStatus.MODEL_SELECTED,
        model=model,
    )

    assert execution.status == (
        OperatorExecutionStatus.MODEL_SELECTED
    )

    assert execution.model == model.name
    assert execution.provider == model.provider
    assert execution.provider_model == model.provider_model


def test_operator_records_execution_error():

    operator = AIModelOperator()

    execution = operator.create_execution(
        "diagnosis",
    )

    operator.update_execution(
        execution,
        OperatorExecutionStatus.FAILED,
        error="model unavailable",
    )

    assert execution.status == OperatorExecutionStatus.FAILED
    assert execution.error == "model unavailable"


def test_selection_updates_execution_lifecycle():

    operator = AIModelOperator()

    execution = operator.create_execution(
        "diagnosis",
    )

    class Runtime:

        def status(self):
            return [
                type(
                    "State",
                    (),
                    {
                        "model": "qwen_reasoning_9b",
                        "installed": True,
                    },
                )(),
            ]

    model = operator.select(
        "diagnosis",
        Runtime(),
        execution=execution,
    )

    assert model is not None

    assert execution.status == (
        OperatorExecutionStatus.MODEL_SELECTED
    )

    assert execution.model == model.name
    assert execution.provider == model.provider
    assert execution.provider_model == model.provider_model


def test_selection_without_available_model_fails_execution():

    operator = AIModelOperator()

    execution = operator.create_execution(
        "diagnosis",
    )

    class Runtime:

        def status(self):
            return []

    model = operator.select(
        "diagnosis",
        Runtime(),
        execution=execution,
    )

    assert model is None

    assert execution.status == (
        OperatorExecutionStatus.FAILED
    )

    assert execution.error == "no_available_model"


def test_selection_without_execution_preserves_existing_contract():

    operator = AIModelOperator()

    class Runtime:

        def status(self):
            return [
                type(
                    "State",
                    (),
                    {
                        "model": "qwen_reasoning_9b",
                        "installed": True,
                    },
                )(),
            ]

    model = operator.select(
        "diagnosis",
        Runtime(),
    )

    assert model is not None
    assert model.name == "qwen_reasoning_9b"

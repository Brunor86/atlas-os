from atlas.services.ai.service import (
    _canonical_execution_action,
    _operation_action_is_executable,
)


def test_canonical_execution_action_from_operation_plan():

    assert (
        _canonical_execution_action(
            "restart",
            "vm",
        )
        == "restart vm"
    )

    assert (
        _canonical_execution_action(
            "stop",
            "lxc",
        )
        == "stop lxc"
    )


def test_executable_vm_operation_uses_execution_truth():

    assert (
        _operation_action_is_executable(
            "restart",
            "vm",
        )
        is True
    )


def test_executable_lxc_restart_uses_execution_truth():

    assert (
        _operation_action_is_executable(
            "restart",
            "lxc",
        )
        is True
    )


def test_lxc_start_stop_use_execution_truth():

    assert (
        _operation_action_is_executable(
            "start",
            "lxc",
        )
        is True
    )

    assert (
        _operation_action_is_executable(
            "stop",
            "lxc",
        )
        is True
    )


def test_missing_operation_components_are_not_executable():

    assert (
        _canonical_execution_action(
            None,
            "vm",
        )
        is None
    )

    assert (
        _operation_action_is_executable(
            None,
            "vm",
        )
        is False
    )

def test_mcp_proposal_construction_is_guarded_by_execution_capability():

    import ast
    import inspect
    import textwrap

    from atlas.services.ai.service import (
        AIService,
    )

    source = textwrap.dedent(
        inspect.getsource(
            AIService.ask_operator
        )
    )

    tree = ast.parse(
        source
    )

    client_calls = []

    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        func = node.func

        if (
            isinstance(
                func,
                ast.Name,
            )
            and func.id
            == "MCPOperatorClient"
        ):

            client_calls.append(
                node
            )


    assert len(
        client_calls
    ) == 1


    def contains_node(
        root,
        target,
    ):

        return any(
            candidate is target
            for candidate in ast.walk(
                root
            )
        )


    guarded = False

    for candidate in ast.walk(
        tree
    ):

        if not isinstance(
            candidate,
            ast.If,
        ):
            continue

        if not contains_node(
            candidate,
            client_calls[0],
        ):
            continue

        condition = ast.unparse(
            candidate.test
        )

        if (
            "operation_executable"
            in condition
        ):

            guarded = True
            break


    assert guarded is True

    assert (
        "execution capability unavailable for action"
        in source
    )

    assert (
        '"operation_blocked"'
        in source
    )

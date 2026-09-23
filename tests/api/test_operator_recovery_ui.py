from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

JS = (
    ROOT
    / "src/atlas/api/static/js/atlas.js"
)

CSS = (
    ROOT
    / "src/atlas/api/static/css/atlas.css"
)


def normalized(
    path,
):

    return " ".join(
        path.read_text().split()
    )


def test_recovery_required_is_handled_before_success_ui():

    source = normalized(JS)

    recovery = (
        'executionState.state '
        '=== "RECOVERY_REQUIRED"'
    )

    success = (
        'execution.status '
        '!== "SUCCESS"'
    )

    assert recovery in source
    assert success in source

    assert (
        source.index(recovery)
        < source.index(success)
    )


def test_recovery_ui_uses_read_only_reverify_endpoint():

    source = normalized(JS)

    assert (
        "/reverify"
        in source
    )

    assert (
        "Manual re-verification"
        in source
    )

    assert (
        "expected_state"
        in source
    )

    assert (
        "observed_state"
        in source
    )

    assert (
        "It does not repeat the original action"
        in source
    )


def test_recovery_ui_has_explicit_visual_state():

    source = normalized(CSS)

    assert (
        ".atlas-operator-status.recovery"
        in source
    )

    assert (
        ".atlas-operator-result.recovery"
        in source
    )

    assert (
        ".atlas-operator-reverify"
        in source
    )

    assert (
        ".atlas-operator-recovery-grid"
        in source
    )

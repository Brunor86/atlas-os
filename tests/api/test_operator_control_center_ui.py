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

HTML = (
    ROOT
    / "src/atlas/api/templates/partials/"
    / "operator_control_center.html"
)


def normalized(
    path,
):

    return " ".join(
        path.read_text().split()
    )


def test_control_center_is_present_and_uses_operator_api():

    js = normalized(JS)
    html = normalized(HTML)

    assert "operatorControlCenter" in html

    assert (
        '"/api/operator/actions"'
        in js
    )

    assert (
        "PENDING_APPROVAL"
        in js
    )

    assert (
        "RECOVERY_REQUIRED"
        in js
    )


def test_control_center_only_uses_existing_operator_actions():

    js = normalized(JS)
    css = normalized(CSS)

    assert "/approve" in js
    assert "/reject" in js
    assert "/reverify" in js

    assert "operator-control-center" in css
    assert "operator-state.verified" in css

    forbidden = (
        "docker restart",
        "docker stop",
        "systemctl",
        "pct restart",
        "qm start",
        "subprocess",
    )

    control_section = js[
        js.index(
            "ATLAS OPERATOR CONTROL CENTER V1"
        ):
        js.index(
            "form.addEventListener",
            js.index(
                "ATLAS OPERATOR CONTROL CENTER V1"
            ),
        )
    ]

    for value in forbidden:
        assert value not in control_section



def test_pending_actions_wire_both_decision_controls():

    js = normalized(JS)

    control_start = js.index(
        "ATLAS OPERATOR CONTROL CENTER V1"
    )

    control_end = js.index(
        "form.addEventListener",
        control_start,
    )

    control = js[
        control_start:
        control_end
    ]

    assert (
        'data-operator-action="reject"'
        in control
    )

    assert (
        'data-operator-action="approve"'
        in control
    )

    assert (
        '.querySelectorAll( '
        '"[data-operator-action]"'
        in control
    )

    assert (
        'operation === "approve"'
        in control
    )

    assert (
        'operation === "reject"'
        in control
    )

    assert (
        'operation === "reverify"'
        in control
    )



def test_operator_auth_uses_explicit_inline_session_controls():

    js = normalized(JS)
    html = normalized(HTML)

    assert (
        "id=\"operatorControlAuthState\""
        in html
    )

    assert (
        "id=\"operatorControlToken\""
        in html
    )

    assert (
        "type=\"password\""
        in html
    )

    assert (
        "id=\"operatorControlUnlock\""
        in html
    )

    assert (
        "id=\"operatorControlLock\""
        in html
    )

    assert (
        "window.prompt("
        not in js
    )

    assert (
        "getStoredOperatorToken"
        in js
    )

    assert (
        "unlockOperatorControlCenter"
        in js
    )

    assert (
        "lockOperatorControlCenter"
        in js
    )


def test_operator_session_has_explicit_locked_and_unlocked_states():

    js = normalized(JS)
    css = normalized(CSS)

    assert (
        ".operator-auth-state.locked"
        in css
    )

    assert (
        ".operator-auth-state.unlocked"
        in css
    )

    assert (
        "setOperatorControlAuthState"
        in js
    )

    assert (
        "sessionStorage.getItem"
        in js
    )

    assert (
        "sessionStorage.setItem"
        in js
    )

    assert (
        "sessionStorage.removeItem"
        in js
    )

    assert (
        "Operator locked."
        in js
    )

from datetime import (
    datetime,
    timezone,
)

import pytest

from atlas.services.sentinel import (
    SentinelEngine,
    SentinelFinding,
    SentinelLiveResult,
    SentinelNotification,
    SentinelRunResult,
    SentinelRuntime,
    SentinelSeverity,
    SentinelSourceResult,
    SentinelState,
    SentinelStateStore,
)
from atlas.services.sentinel.rendering import (
    SentinelMessageRenderer,
)
from atlas.services.sentinel.telegram import (
    TelegramConfig,
    TelegramNotifier,
)


NOW = datetime(
    2026,
    10,
    7,
    3,
    0,
    tzinfo=timezone.utc,
)


def make_finding():
    return SentinelFinding(
        fingerprint="sentinel:v1:test",
        source="backup",
        kind="backup_protection_gap",
        subject="backup_inventory",
        severity=SentinelSeverity.WARNING,
        state=SentinelState.OPEN,
        title=(
            "Backup protection "
            "requires attention"
        ),
        summary=(
            "1 missing backup target."
        ),
        observed_at=NOW,
        evidence={
            "missing": 1,
        },
    )


class FakeLiveService:
    def __init__(
        self,
        finding,
    ):
        self.finding = finding

    def dry_run(
        self,
        *,
        previous_state=None,
    ):
        engine = (
            SentinelEngine()
        )

        evaluation = (
            engine.evaluate(
                [self.finding],
                previous_state or {},
                observed_at=NOW,
            )
        )

        return SentinelLiveResult(
            collected_at=NOW,
            sources=(
                SentinelSourceResult(
                    source="backup",
                    findings=(
                        self.finding,
                    ),
                ),
            ),
            evaluation=evaluation,
        )


class FakeNotifier:
    def __init__(
        self,
        *,
        fail=False,
    ):
        self.fail = fail
        self.sent = []

    def send(
        self,
        notification,
    ):
        self.sent.append(
            notification
        )

        if self.fail:
            raise RuntimeError(
                "telegram unavailable"
            )

        return {
            "message_id": 123,
        }


def test_state_store_roundtrip(
    tmp_path,
):
    finding = make_finding()

    path = (
        tmp_path
        / "state.json"
    )

    store = SentinelStateStore(
        path
    )

    store.save(
        {
            finding.fingerprint:
                finding,
        }
    )

    loaded = store.load()

    assert (
        loaded[
            finding.fingerprint
        ]
        == finding
    )

    assert (
        path.stat().st_mode
        & 0o777
        == 0o600
    )


def test_dry_run_does_not_save_state(
    tmp_path,
):
    path = (
        tmp_path
        / "state.json"
    )

    runtime = SentinelRuntime(
        live_service=(
            FakeLiveService(
                make_finding()
            )
        ),
        state_store=(
            SentinelStateStore(
                path
            )
        ),
    )

    result = runtime.run(
        dry_run=True
    )

    assert (
        result.state_saved
        is False
    )

    assert not path.exists()


def test_successful_delivery_saves_state(
    tmp_path,
):
    path = (
        tmp_path
        / "state.json"
    )

    notifier = (
        FakeNotifier()
    )

    runtime = SentinelRuntime(
        live_service=(
            FakeLiveService(
                make_finding()
            )
        ),
        state_store=(
            SentinelStateStore(
                path
            )
        ),
        notifier=notifier,
    )

    result = runtime.run(
        dry_run=False
    )

    assert len(
        notifier.sent
    ) == 1

    assert result.state_saved
    assert path.exists()


def test_failed_delivery_does_not_advance_state(
    tmp_path,
):
    path = (
        tmp_path
        / "state.json"
    )

    runtime = SentinelRuntime(
        live_service=(
            FakeLiveService(
                make_finding()
            )
        ),
        state_store=(
            SentinelStateStore(
                path
            )
        ),
        notifier=(
            FakeNotifier(
                fail=True
            )
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="telegram unavailable",
    ):
        runtime.run(
            dry_run=False
        )

    assert not path.exists()


def test_renderer_is_human_readable():
    finding = make_finding()

    notification = (
        SentinelNotification(
            finding=finding,
            reason="new_warning",
        )
    )

    text = (
        SentinelMessageRenderer()
        .render(
            notification
        )
    )

    assert (
        "⚠️ ATLAS SENTINEL · WARNING"
        in text
    )

    assert (
        "Backup protection"
        in text
    )

    assert (
        "1 missing backup target"
        in text
    )


class FakeResponse:
    def raise_for_status(
        self,
    ):
        return None

    def json(
        self,
    ):
        return {
            "ok": True,
            "result": {
                "message_id": 77,
                "chat": {
                    "id": 1234,
                },
            },
        }


class FakeHttpClient:
    def __init__(
        self,
    ):
        self.calls = []

    def post(
        self,
        url,
        *,
        json,
    ):
        self.calls.append(
            (
                url,
                json,
            )
        )

        return FakeResponse()


def test_telegram_transport_uses_send_message():
    client = (
        FakeHttpClient()
    )

    notifier = TelegramNotifier(
        config=TelegramConfig(
            bot_token="secret-test-token",
            chat_id="1234",
        ),
        client=client,
    )

    notification = (
        SentinelNotification(
            finding=make_finding(),
            reason="new_warning",
        )
    )

    result = notifier.send(
        notification
    )

    assert (
        result["message_id"]
        == 77
    )

    assert len(
        client.calls
    ) == 1

    url, body = (
        client.calls[0]
    )

    assert (
        url.endswith(
            "/sendMessage"
        )
    )

    assert (
        body["chat_id"]
        == "1234"
    )

    assert (
        "secret-test-token"
        not in body["text"]
    )

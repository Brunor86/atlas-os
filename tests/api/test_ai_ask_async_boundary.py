import asyncio
from types import SimpleNamespace

from atlas.api import server


class DummyRequest:

    async def json(self):

        return {
            "question":
                "Reiniciá olivasat",
        }


class FakeAIService:

    def ask_operator(
        self,
        request,
    ):

        asyncio.run(
            asyncio.sleep(
                0
            )
        )

        return SimpleNamespace(
            content=(
                "ATLAS prepared an "
                "operation proposal."
            ),
            latency_ms=1.0,
            model="test",
            provider="test",
            metadata={
                "llm_used": True,
                "planner_calls": 1,
            },
        )


def test_ai_ask_moves_sync_operator_outside_running_event_loop(
    monkeypatch,
):

    monkeypatch.setattr(
        server,
        "ai_service",
        FakeAIService(),
    )

    result = asyncio.run(
        server.ai_ask(
            DummyRequest()
        )
    )

    assert (
        result["status"]
        == "SUCCESS"
    )

    assert (
        result["execution"][
            "llm_used"
        ]
        is True
    )

    assert (
        result["execution"][
            "planner_calls"
        ]
        == 1
    )

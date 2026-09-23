from atlas.services.ai.llm.ollama import OllamaProvider


class FakeResponse:

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "response":
                '{"action":"final","answer":"ok"}'
        }


def test_generate_can_disable_thinking(
    monkeypatch,
):

    captured = {}

    def fake_post(
        url,
        *,
        json,
        timeout,
    ):
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(
        "atlas.services.ai.llm.ollama.requests.post",
        fake_post,
    )

    provider = OllamaProvider(
        host="http://ollama.example:11434"
    )

    provider.generate(
        "Return JSON only",
        model="qwen3.5:9b",
        temperature=0,
        max_tokens=500,
        keep_alive="5m",
        think=False,
    )

    assert captured["payload"]["think"] is False
    assert (
        captured["payload"]["options"]["num_predict"]
        == 500
    )
    assert (
        captured["payload"]["options"]["temperature"]
        == 0
    )
    assert captured["payload"]["keep_alive"] == "5m"


def test_generate_preserves_default_thinking_behavior(
    monkeypatch,
):

    captured = {}

    def fake_post(
        url,
        *,
        json,
        timeout,
    ):
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(
        "atlas.services.ai.llm.ollama.requests.post",
        fake_post,
    )

    provider = OllamaProvider(
        host="http://ollama.example:11434"
    )

    provider.generate(
        "Reason about this",
        model="qwen3.5:9b",
    )

    assert "think" not in captured["payload"]

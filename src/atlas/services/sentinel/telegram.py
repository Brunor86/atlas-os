import os
from dataclasses import dataclass

import httpx

from atlas.services.sentinel.rendering import (
    SentinelMessageRenderer,
)


@dataclass(
    frozen=True,
    slots=True,
)
class TelegramConfig:
    bot_token: str
    chat_id: str

    @classmethod
    def from_env(
        cls,
    ):
        token = (
            os.environ.get(
                "ATLAS_TELEGRAM_BOT_TOKEN"
            )
            or ""
        ).strip()

        chat_id = (
            os.environ.get(
                "ATLAS_TELEGRAM_CHAT_ID"
            )
            or ""
        ).strip()

        if not token:
            raise RuntimeError(
                "ATLAS_TELEGRAM_BOT_TOKEN "
                "is not configured"
            )

        if not chat_id:
            raise RuntimeError(
                "ATLAS_TELEGRAM_CHAT_ID "
                "is not configured"
            )

        return cls(
            bot_token=token,
            chat_id=chat_id,
        )


class TelegramNotifier:
    def __init__(
        self,
        *,
        config=None,
        client=None,
        renderer=None,
    ):
        self.config = (
            config
            or TelegramConfig.from_env()
        )

        self.client = (
            client
            or httpx.Client(
                timeout=10.0
            )
        )

        self.renderer = (
            renderer
            or SentinelMessageRenderer()
        )

    def _url(
        self,
        method,
    ):
        return (
            "https://api.telegram.org/"
            f"bot{self.config.bot_token}/"
            f"{method}"
        )

    def send(
        self,
        notification,
    ):
        text = self.renderer.render(
            notification
        )

        response = self.client.post(
            self._url(
                "sendMessage"
            ),
            json={
                "chat_id":
                    self.config.chat_id,
                "text":
                    text,
                "disable_web_page_preview":
                    True,
            },
        )

        response.raise_for_status()

        payload = response.json()

        if not payload.get(
            "ok"
        ):
            raise RuntimeError(
                "Telegram API rejected "
                "Sentinel notification"
            )

        result = (
            payload.get("result")
            or {}
        )

        return {
            "message_id":
                result.get(
                    "message_id"
                ),
            "chat_id":
                (
                    result.get("chat")
                    or {}
                ).get("id"),
        }

    def probe(
        self,
    ):
        response = self.client.get(
            self._url(
                "getMe"
            )
        )

        response.raise_for_status()

        payload = response.json()

        if not payload.get(
            "ok"
        ):
            raise RuntimeError(
                "Telegram bot probe failed"
            )

        result = (
            payload.get("result")
            or {}
        )

        return {
            "id":
                result.get("id"),
            "username":
                result.get("username"),
            "name":
                result.get("first_name"),
        }

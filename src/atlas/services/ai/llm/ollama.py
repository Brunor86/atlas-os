import os

import requests

from atlas.services.ai.llm.base import LLMProvider


class OllamaProvider(LLMProvider):

    def __init__(
        self,
        host: str = "http://127.0.0.1:11434",
        timeout: int = 120,
        verify: bool | None = None,
    ):

        self.host = host.rstrip("/")
        self.timeout = timeout

        if verify is None:
            verify = (
                os.getenv(
                    "ATLAS_OLLAMA_VERIFY_SSL",
                    "true",
                ).lower()
                == "true"
            )

        self.verify = verify


    def available(self) -> bool:

        try:

            r = requests.get(
                f"{self.host}/api/tags",
                timeout=2,
            )

            return r.status_code == 200


        except Exception:

            return False



    def models(self) -> list[str]:

        try:

            r = requests.get(
                f"{self.host}/api/tags",
                timeout=2,
            )

            r.raise_for_status()

            data = r.json()


            return [

                model.get("name")

                for model in data.get(
                    "models",
                    []
                )

                if model.get("name")

            ]


        except Exception:

            return []




    def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        tools: list[dict] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        keep_alive: int | str = 0,
    ) -> dict:

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if tools:
            payload["tools"] = tools

        r = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=self.timeout,
        )

        r.raise_for_status()

        return r.json()



    def generate_with_tools(
        self,
        messages,
        tools,
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        keep_alive: int | str = 0,
    ):
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "keep_alive": keep_alive,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        response = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=self.timeout,
            verify=self.verify,
        )

        response.raise_for_status()

        data = response.json()

        print(
            "[OLLAMA METRICS]",
            {
                "model": data.get("model"),
                "total_duration": data.get("total_duration"),
                "load_duration": data.get("load_duration"),
                "prompt_eval_duration": data.get("prompt_eval_duration"),
                "eval_duration": data.get("eval_duration"),
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
            }
        )

        return data

    def unload(
        self,
        model: str,
    ) -> None:
        """
        Force Ollama to unload a model immediately.
        """

        payload = {
            "model": model,
            "prompt": "",
            "stream": False,
            "keep_alive": 0,
        }

        r = requests.post(
            f"{self.host}/api/generate",
            json=payload,
            timeout=10,
        )

        r.raise_for_status()


    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        keep_alive: int | str = 0,
        think: bool | None = None,
    ) -> str:


        payload = {

            "model": model,

            "prompt": prompt,

            "stream": False,

            # Important:
            # 0 tells Ollama to unload the model after generation.
            # This prevents the 14B fallback from remaining resident.
            "keep_alive": keep_alive,

            "options":
            {
                "temperature": temperature,

                "num_predict": max_tokens,
            },

        }


        if system:

            payload["system"] = system


        # Thinking is request-specific.
        #
        # Reasoning workloads may keep the model default, while
        # bounded protocols can explicitly disable thinking.
        if think is not None:

            payload["think"] = think



        r = requests.post(

            f"{self.host}/api/generate",

            json=payload,

            timeout=self.timeout,

        )


        r.raise_for_status()


        data = r.json()


        return data.get(
            "response",
            "",
        )

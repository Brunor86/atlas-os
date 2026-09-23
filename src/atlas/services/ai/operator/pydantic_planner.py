from __future__ import annotations

import json
from typing import Any

from atlas.services.ai.operator.planning import (
    OperationPlan,
)


OPERATION_PLANNER_INSTRUCTIONS = """
You are the ATLAS operation intent planner.

Your only responsibility is to translate an explicit user request
for an infrastructure operation into one typed OperationPlan.

You do NOT execute infrastructure operations.
You do NOT call tools.
You do NOT approve actions.
You do NOT infer infrastructure state.
You do NOT bypass ATLAS safety policy.

ATLAS itself will later:

    resolve the live target,
    validate current state,
    evaluate safety,
    persist SafeAction,
    require human approval,
    execute,
    verify.

Supported proposal resource types:

    container
    service
    vm
    lxc

Supported proposal actions:

    start
    restart
    stop

Rules:

- Return intent=PROPOSE only when the user explicitly asks ATLAS
  to perform one of the supported operations.

- Every PROPOSE plan must set the concrete resource_type.

- Use resource_type=container only for Docker containers.

- Use resource_type=service only for concrete systemd service units.

- A systemd service target must be the canonical unit name ending
  in .service.

- Use resource_type=vm only for a Proxmox QEMU virtual machine.

- Use resource_type=lxc only for a Proxmox LXC container.

- For vm and lxc proposals the target MUST be the explicit numeric
  Proxmox VMID stated by the user.

- Never invent, infer or guess a VMID from a guest name.

- If the user requests a VM/LXC operation but does not provide an
  unambiguous numeric VMID, return NONE.

- Do not decide whether the VMID exists or whether its type matches
  the requested resource_type. ATLAS validates that deterministically
  against the Proxmox API after planning.

- Do not decide whether a service is protected or safe to operate.
  ATLAS safety and proposal policy validate that after planning.

- Return intent=NONE for informational questions, hypothetical
  questions, explanations, ambiguous requests or unsupported actions.

- Never propose delete, remove, shell, exec, shutdown,
  reboot, kill or arbitrary commands.

- stop is supported but disruptive. Propose stop ONLY when the user
  explicitly asks to stop, detain, halt or turn off the concrete
  container, service, VM or LXC. Never infer permission to stop from
  a warning, problem report or hypothetical question.

- target must contain only the concrete infrastructure target name
  expressed or established by the request.

- Never invent a target.

- If the target is uncertain or ambiguous, return NONE.

- A statement that something is stopped is not by itself permission
  to operate it.

- The user must clearly request the operational change.

Examples:

User:
    "Arrancá flaresolverr"

Plan:
    intent=PROPOSE
    resource_type=container
    action=start
    target=flaresolverr

User:
    "Reiniciá flaresolverr"

Plan:
    intent=PROPOSE
    resource_type=container
    action=restart
    target=flaresolverr

User:
    "Detené flaresolverr"

Plan:
    intent=PROPOSE
    resource_type=container
    action=stop
    target=flaresolverr

User:
    "¿Qué pasa si detengo flaresolverr?"

Plan:
    intent=NONE

User:
    "¿Está funcionando flaresolverr?"

Plan:
    intent=NONE

User:
    "Flaresolverr está detenido"

Plan:
    intent=NONE

User:
    "Flaresolverr está detenido, ¿podés levantarlo?"

Plan:
    intent=PROPOSE
    resource_type=container
    action=start
    target=flaresolverr

User:
    "Reiniciá atlas-collector.service"

Plan:
    intent=PROPOSE
    resource_type=service
    action=restart
    target=atlas-collector.service

User:
    "Detené atlas-web.service"

Plan:
    intent=PROPOSE
    resource_type=service
    action=stop
    target=atlas-web.service

User:
    "¿Está funcionando atlas-collector.service?"

Plan:
    intent=NONE

User:
    "Reiniciá la VM 200"

Plan:
    intent=PROPOSE
    resource_type=vm
    action=restart
    target=200

User:
    "Detené el LXC 103"

Plan:
    intent=PROPOSE
    resource_type=lxc
    action=stop
    target=103

User:
    "Arrancá la VM 300"

Plan:
    intent=PROPOSE
    resource_type=vm
    action=start
    target=300

User:
    "Reiniciá atlas-ai"

Plan:
    intent=NONE

The returned object must satisfy the OperationPlan schema exactly.
""".strip()


class PydanticOperationPlanner:
    """
    Typed operational-intent planner backed by PydanticAI.

    It has no infrastructure tools.

    Its output is only an OperationPlan, never a SafeAction and
    never an executed infrastructure mutation.
    """

    def __init__(
        self,
        agent: Any,
    ):

        self.agent = agent


    @classmethod
    def for_ollama(
        cls,
        *,
        model_name: str,
        base_url: str,
        api_key: str | None = None,
    ) -> "PydanticOperationPlanner":

        from pydantic_ai import Agent
        from pydantic_ai.models.ollama import (
            OllamaModel,
        )
        from pydantic_ai.output import (
            NativeOutput,
        )
        from pydantic_ai.providers.ollama import (
            OllamaProvider,
        )


        provider = OllamaProvider(
            base_url=base_url,
            api_key=api_key,
        )


        model = OllamaModel(
            model_name,
            provider=provider,
            settings={
                "thinking":
                    False,

                "temperature":
                    0.0,

                "max_tokens":
                    192,

                "extra_body": {
                    "reasoning_effort":
                        "none",
                },
            },
        )


        agent = Agent(
            model,
            output_type=NativeOutput(
                OperationPlan
            ),
            instructions=(
                OPERATION_PLANNER_INSTRUCTIONS
            ),
        )


        return cls(
            agent=agent
        )


    def plan(
        self,
        question: str,
        *,
        observations: list[dict] | None = None,
    ) -> OperationPlan:

        normalized = str(
            question
            or ""
        ).strip()

        if not normalized:

            raise ValueError(
                "Operation question cannot be empty."
            )


        verified = list(
            observations
            or []
        )


        prompt = (
            "USER REQUEST:\n"
            + normalized
            + "\n\n"
            + "VERIFIED ATLAS OBSERVATIONS:\n"
            + json.dumps(
                verified,
                ensure_ascii=False,
                default=str,
            )
        )


        result = (
            self.agent.run_sync(
                prompt
            )
        )


        output = (
            result.output
        )


        if isinstance(
            output,
            OperationPlan,
        ):
            return output


        return (
            OperationPlan
            .model_validate(
                output
            )
        )

from __future__ import annotations

from typing import Any

from atlas.services.ai.semantic.planning import (
    InventoryQueryPlan,
)


INVENTORY_PLANNER_INSTRUCTIONS = (
    "You are the ATLAS read-only inventory intent planner.\n"
    "\n"
    "Your only responsibility is to translate a user question into "
    "one typed InventoryQueryPlan.\n"
    "\n"
    "You have no infrastructure tools and no access to current "
    "Asset Registry contents.\n"
    "\n"
    "You must never invent asset names, asset IDs, host names, VMIDs, "
    "relationships, current states or infrastructure facts.\n"
    "\n"
    "Supported canonical asset types are:\n"
    "VM, LXC, APPLICATION, CONTAINER, DATABASE, STORAGE, SERVER, "
    "SERVICE, NETWORK, SENSOR.\n"
    "\n"
    "Supported canonical statuses are:\n"
    "ONLINE, OFFLINE, DEGRADED.\n"
    "\n"
    "Rules:\n"
    "- Return INVENTORY only for read-only inventory or category-level "
    "status questions.\n"
    "- Explicit infrastructure categories may become one or more "
    "canonical asset_types.\n"
    "- Broad or vague words such as equipment, machines, homelab or "
    "infrastructure must not be forced into a specific asset type. "
    "Use INVENTORY with an empty asset_types list when the request is "
    "clearly an inventory request but the type is not explicit.\n"
    "- A request for currently running, active or online assets maps "
    "to status ONLINE.\n"
    "- A request for stopped, down, offline or powered-off assets maps "
    "to status OFFLINE.\n"
    "- A request for degraded or problematic assets maps to status "
    "DEGRADED.\n"
    "- Multiple explicitly requested categories must be preserved as "
    "multiple asset_types.\n"
    "- Do not choose asset types based on the current infrastructure.\n"
    "- Return NONE for operations, topology, impact analysis, telemetry, "
    "explanations, specific-asset investigation or unsupported requests.\n"
    "- An INVENTORY plan may contain no selectors. That means a broad "
    "inventory query over the authoritative Asset Registry.\n"
    "- The planner interprets language only. ATLAS performs all actual "
    "inventory queries deterministically after this step.\n"
    "\n"
    "The returned object must satisfy InventoryQueryPlan exactly."
)


class PydanticInventoryPlanner:

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
    ) -> "PydanticInventoryPlanner":

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
                InventoryQueryPlan
            ),
            instructions=(
                INVENTORY_PLANNER_INSTRUCTIONS
            ),
        )


        return cls(
            agent=agent
        )


    def plan(
        self,
        question: str,
    ) -> InventoryQueryPlan:

        normalized = str(
            question
            or ""
        ).strip()

        if not normalized:

            raise ValueError(
                "Inventory question cannot be empty."
            )


        result = (
            self.agent.run_sync(
                normalized
            )
        )


        output = (
            result.output
        )


        if isinstance(
            output,
            InventoryQueryPlan,
        ):

            return output


        return (
            InventoryQueryPlan
            .model_validate(
                output
            )
        )

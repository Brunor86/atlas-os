from __future__ import annotations

from typing import Any

from atlas.services.ai.investigator.planning import (
    InvestigationPlan,
)


PLANNER_INSTRUCTIONS = """
You are the ATLAS investigation planner.

Your only responsibility is to translate the user's infrastructure
question into one structured InvestigationPlan.

You do not know infrastructure facts.
You do not answer the user's question.
You do not infer current infrastructure state.
You do not call infrastructure tools.

ATLAS itself will resolve entities, query knowledge, collect evidence,
validate scope and decide which facts are admissible.

Planning rules:

- RELATION:
  identify the relationship requested and whether the target is the
  SUBJECT or OBJECT of the canonical relationship.

- STATUS:
  use STATUS for current canonical inventory state.

  STATUS fields are STRUCTURED SELECTORS. Never encode filters,
  predicates, SQL, expressions, wildcard queries or a mini-language
  inside collection_query.

  For a COLLECTION status question:

      collection_query
          contains only the human-readable collection concept,
          such as "applications", "servers" or "monitoring nodes".

      asset_type
          contains a canonical ATLAS asset type when requested,
          such as APPLICATION, SERVER, VM, LXC, SERVICE or STORAGE.

      role
          contains a canonical ATLAS asset role when requested.

      criticality
          contains LOW, MEDIUM, HIGH or CRITICAL when requested.

      status_filter
          contains the canonical requested status, such as
          ONLINE, OFFLINE, DEGRADED or UNKNOWN.

  A STATUS COLLECTION plan MUST contain at least one canonical
  selector among asset_type, role, criticality and status_filter.

  Example:

      User:
          "¿Qué aplicaciones están offline?"

      Plan semantics:
          domain = STATUS
          scope_mode = COLLECTION
          collection_query = "applications"
          asset_type = APPLICATION
          status_filter = OFFLINE

  Correct:
      collection_query = "applications"
      asset_type = APPLICATION
      status_filter = OFFLINE

  Incorrect:
      collection_query = "*application* WHERE STATUS = 'OFFLINE'"
      asset_type = null
      status_filter = null

  The collection_query field is descriptive only. It is NEVER a query
  language and NEVER substitutes for canonical selectors.

- ATTENTION:
  use for current alerts, incidents, warnings or things needing
  operational attention.

- OBSERVATION:
  use for a specific measured observation or telemetry concept.

- IMPACT:
  use when asking what would be affected by an asset.

- HEALTH:
  use when asking about the health of a concrete asset.

- UNKNOWN:
  use when the request cannot be represented safely by the available
  investigation domains.

Never invent asset identifiers.
Use the user's human-readable wording in target_query or
collection_query when appropriate.

The returned object must satisfy the InvestigationPlan schema exactly.
""".strip()


class PydanticInvestigationPlanner:
    """
    Typed semantic planner backed by PydanticAI.

    The planner has no infrastructure tools and therefore cannot create
    authoritative ATLAS facts. Its output is only an InvestigationPlan.

    Infrastructure authority remains with:

        Semantic API
        MCP atlas-knowledge
        EvidenceLedger
        InvestigationScope
        deterministic validation
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
    ) -> "PydanticInvestigationPlanner":
        """
        Build a PydanticAI planner for a self-hosted/remote Ollama
        OpenAI-compatible endpoint.

        No network request is made merely by constructing the planner.
        """

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
                #
                # The planner performs bounded semantic extraction.
                # It does not need open-ended model reasoning.
                #
                # Keep the unified PydanticAI intent explicit, while
                # also enforcing the Ollama OpenAI-compatible request
                # field that actually disables Qwen reasoning.
                #
                "thinking":
                    False,

                "temperature":
                    0.0,

                "max_tokens":
                    256,

                "extra_body":
                    {
                        "reasoning_effort":
                            "none",
                    },
            },
        )

        agent = Agent(
            model,
            output_type=NativeOutput(
                InvestigationPlan
            ),
            instructions=PLANNER_INSTRUCTIONS,
        )

        return cls(
            agent=agent
        )

    def plan(
        self,
        question: str,
    ) -> InvestigationPlan:
        """
        Produce one schema-validated semantic investigation plan.
        """

        normalized = str(
            question
            or ""
        ).strip()

        if not normalized:
            raise ValueError(
                "Investigation question cannot be empty."
            )

        result = self.agent.run_sync(
            normalized
        )

        output = result.output

        if isinstance(
            output,
            InvestigationPlan,
        ):
            return output

        #
        # Keep an explicit validation boundary even for injected/fake
        # agents and future provider implementations.
        #
        return InvestigationPlan.model_validate(
            output
        )

import json
import time


class OperatorAgent:

    def __init__(
        self,
        ai_service,
        max_steps=5,
        *,
        tool_backend=None,
        planner=None,
        semantic_preflight=True,
        tool_preflight=True,
        event_callback=None,
    ):

        self.ai = ai_service

        self.max_steps = max_steps

        self.tool_backend = (
            tool_backend
        )

        self.planner = planner

        self.semantic_preflight = (
            semantic_preflight
        )

        self.tool_preflight = (
            tool_preflight
        )

        self.event_callback = (
            event_callback
        )

        self._planner_calls = 0


    def _emit(
        self,
        event,
        **data,
    ):
        """
        Emit observable operator activity.

        Events contain execution facts only.
        Model reasoning / chain-of-thought is never emitted.

        Observability must never alter operator execution, therefore
        callback failures are isolated from the agent.
        """

        callback = (
            self.event_callback
        )

        if not callable(
            callback
        ):
            return

        try:

            callback(
                event,
                data,
            )

        except Exception:

            return


    def _raw_tools(self):

        if self.tool_backend is not None:

            return (
                self.tool_backend
                .list_tools()
            )

        return self.ai.list_tools()


    def _tool_descriptions(self):

        tools = self._raw_tools()

        descriptions = []

        for tool in tools:

            if isinstance(
                tool,
                dict,
            ):

                read_only = tool.get(
                    "read_only",
                    False,
                )

                requires_approval = (
                    tool.get(
                        "requires_approval",
                        False,
                    )
                )

                if (
                    not read_only
                    or requires_approval
                ):
                    continue

                descriptions.append(
                    {
                        "name":
                            tool.get(
                                "name"
                            ),

                        "description":
                            tool.get(
                                "description",
                                "",
                            ),

                        "read_only":
                            True,

                        "requires_approval":
                            False,

                        "parameters":
                            tool.get(
                                "parameters",
                                {
                                    "type":
                                        "object",
                                    "properties":
                                        {},
                                },
                            ),
                    }
                )

                continue

            if (
                not tool["read_only"]
                or tool["requires_approval"]
            ):
                continue

            descriptions.append(
                {
                    "name":
                        tool["name"],

                    "description":
                        tool["description"],

                    "read_only":
                        True,

                    "requires_approval":
                        False,

                    "parameters":
                        tool.get(
                            "parameters",
                            {
                                "type":
                                    "object",
                                "properties":
                                    {},
                            },
                        ),
                }
            )

        return descriptions


    def _execute_tool(
        self,
        name,
        arguments,
    ):

        if self.tool_backend is not None:

            return (
                self.tool_backend
                .execute_tool(
                    name,
                    **arguments,
                )
            )

        return self.ai.execute_tool(
            name,
            **arguments,
        )


    def _ask_planner(
        self,
        request,
    ):

        self._planner_calls += 1

        call_number = (
            self._planner_calls
        )

        self._emit(
            "planner_started",
            call=call_number,
        )

        started = (
            time.perf_counter()
        )

        try:

            if self.planner is not None:

                response = self.planner(
                    request
                )

            else:

                response = self.ai.ask(
                    request
                )

        except Exception as exc:

            latency_ms = (
                time.perf_counter()
                - started
            ) * 1000

            self._emit(
                "planner_failed",
                call=call_number,
                status="ERROR",
                latency_ms=round(
                    latency_ms,
                    2,
                ),
                error=str(exc),
            )

            raise

        latency_ms = getattr(
            response,
            "latency_ms",
            None,
        )

        if latency_ms is None:

            latency_ms = (
                time.perf_counter()
                - started
            ) * 1000

        self._emit(
            "planner_completed",
            call=call_number,
            status="SUCCESS",
            model=getattr(
                response,
                "model",
                None,
            ),
            provider=getattr(
                response,
                "provider",
                None,
            ),
            latency_ms=round(
                float(
                    latency_ms
                    or 0
                ),
                2,
            ),
        )

        return response


    def _build_prompt(
        self,
        user_request,
        observations,
    ):

        tools = self._tool_descriptions()

        return f"""
You are ATLAS, an infrastructure knowledge agent.

Your job is to investigate the user's real infrastructure using
ONLY the read-only tools listed below.

You MUST NOT invent infrastructure facts.

Available read-only tools and their argument schemas:

{json.dumps(tools, indent=2, ensure_ascii=False)}

Previous verified tool observations:

{json.dumps(observations, indent=2, ensure_ascii=False, default=str)}

User request:

{user_request}

You must return ONLY valid JSON.

If you need to call a tool, return:

{{
  "action": "tool",
  "tool": "tool_name",
  "arguments": {{}},
  "reason": "short reason"
}}

If you have enough verified information to answer, return:

{{
  "action": "final",
  "answer": "your answer"
}}

Rules:

- Only use tools listed above.
- Never invent tool names or arguments.
- Respect the JSON schema of each tool.
- Never execute actions.
- Never request approval.
- Use the minimum number of tool calls necessary.
- Search for an entity before describing or traversing it when
  you do not already have its canonical asset id.
- Relationship semantics are canonical source-to-target semantics.
- DEPENDS_ON means source depends on target.
- To find what X depends on, call atlas_query_relations with
  direction="downstream", relationship="DEPENDS_ON", depth=1.
- To find what depends on X, call atlas_query_relations with
  direction="upstream", relationship="DEPENDS_ON", depth=1.
- When the user asks for all relationships, both directions,
  incoming and outgoing relationships, use atlas_query_relations with
  direction="neighbors", relationship=null, depth up to 3.
- Prefer a relationship filter when the requested relation is known.
- Prefer exact ATLAS evidence over assumptions.
- If ATLAS does not provide enough evidence, say so.
- Do not answer infrastructure facts from pretrained knowledge.
- Return JSON only.
"""


    def _parse_response(
        self,
        content,
    ):

        content = content.strip()

        try:
            return json.loads(
                content
            )
        except json.JSONDecodeError:
            pass

        if "```" in content:

            parts = content.split(
                "```"
            )

            for part in parts:

                candidate = (
                    part.strip()
                )

                if candidate.startswith(
                    "json"
                ):
                    candidate = (
                        candidate[4:]
                        .strip()
                    )

                try:
                    return json.loads(
                        candidate
                    )
                except json.JSONDecodeError:
                    continue

        # Recover the first valid JSON object if the model
        # added harmless prose around the requested JSON.
        decoder = json.JSONDecoder()

        for index, char in enumerate(
            content
        ):

            if char != "{":
                continue

            try:

                value, _ = decoder.raw_decode(
                    content[
                        index:
                    ]
                )

            except json.JSONDecodeError:
                continue

            if (
                isinstance(
                    value,
                    dict,
                )
                and value.get(
                    "action"
                )
                in {
                    "tool",
                    "final",
                }
            ):

                return value

        raise ValueError(
            "Agent model returned invalid JSON"
        )


    def _semantic_fast_path(
        self,
        user_request,
    ):

        if not self.semantic_preflight:
            return None

        semantic_query = getattr(
            self.ai,
            "deterministic_semantic_query",
            None,
        )

        if not callable(
            semantic_query
        ):
            return None

        semantic_result = (
            semantic_query(
                user_request
            )
        )

        if semantic_result is None:
            return None

        synthesizer = getattr(
            self.ai,
            "synthesize_semantic_result",
            None,
        )

        if callable(
            synthesizer
        ):
            answer = synthesizer(
                semantic_result
            )
        else:
            answer = str(
                semantic_result
            )

        return {
            "status":
                "SUCCESS",

            "answer":
                answer,

            "steps":
                1,

            "model":
                "atlas-semantic",

            "provider":
                "atlas",

            "llm_used":
                False,

            "tools_used": [
                "semantic_query",
            ],

            "observations": [
                {
                    "step":
                        1,

                    "tool":
                        "semantic_query",

                    "arguments": {
                        "query":
                            user_request,
                    },

                    "status":
                        "SUCCESS",

                    "result":
                        semantic_result,

                    "error":
                        None,

                    "evidence": [
                        (
                            "deterministic "
                            "semantic plan"
                        ),
                        (
                            "runtime asset "
                            "registry"
                        ),
                    ],
                }
            ],
        }


    def _tool_fast_path(
        self,
        user_request,
    ):

        if not self.tool_preflight:
            return None

        deterministic_tool_query = getattr(
            self.ai,
            "deterministic_tool_query",
            None,
        )

        if not callable(
            deterministic_tool_query
        ):
            return None

        tool_result = (
            deterministic_tool_query(
                user_request
            )
        )

        if tool_result is None:
            return None

        tools = list(
            tool_result.get(
                "tools",
                [],
            )
        )

        return {
            "status":
                "SUCCESS",

            "answer":
                tool_result.get(
                    "content",
                    "",
                ),

            "steps":
                1,

            "model":
                "atlas-tools",

            "provider":
                "atlas",

            "llm_used":
                False,

            "tools_used":
                tools,

            "observations": [
                {
                    "step":
                        1,

                    "tool":
                        (
                            tools[0]
                            if len(tools) == 1
                            else "deterministic_tools"
                        ),

                    "arguments":
                        {},

                    "status":
                        "SUCCESS",

                    "result":
                        tool_result.get(
                            "results",
                            [],
                        ),

                    "error":
                        None,

                    "evidence": [
                        "deterministic tool routing",
                    ],
                }
            ],
        }


    @staticmethod
    def _verified_relation_answer(
        arguments,
        result,
    ):

        if not result.success:

            return None

        relationship = str(
            arguments.get(
                "relationship",
                ""
            )
            or ""
        ).strip().upper()

        direction = str(
            arguments.get(
                "direction",
                ""
            )
            or ""
        ).strip().lower()

        data = (
            result.data
            if isinstance(
                result.data,
                dict,
            )
            else {}
        )

        rows = (
            data.get(
                "results"
            )
            or []
        )

        source = (
            data.get(
                "asset"
            )
            or {}
        )

        source_name = (
            source.get(
                "name"
            )
            or source.get(
                "id"
            )
            or "asset"
        )

        # --------------------------------------------------------
        # VERIFIED UNFILTERED NEIGHBOR SYNTHESIS
        #
        # "neighbors" is the canonical bidirectional relation query.
        # Once MCP has returned those verified rows, do not ask the
        # LLM to serialize the whole result again.
        # --------------------------------------------------------

        if not relationship:

            if direction != "neighbors":

                return None

            entries = []

            for row in rows:

                if not isinstance(
                    row,
                    dict,
                ):
                    continue

                name = (
                    row.get(
                        "name"
                    )
                    or row.get(
                        "asset_id"
                    )
                )

                if not name:
                    continue

                row_relationship = str(
                    row.get(
                        "relationship"
                    )
                    or "RELATION"
                ).strip().upper()

                row_direction = str(
                    row.get(
                        "direction"
                    )
                    or ""
                ).strip().upper()

                if row_direction:

                    entry = (
                        f"{row_direction} · "
                        f"{row_relationship} · "
                        f"{name}"
                    )

                else:

                    entry = (
                        f"{row_relationship} · "
                        f"{name}"
                    )

                if entry not in entries:

                    entries.append(
                        entry
                    )

            if not entries:

                return (
                    "ATLAS no encontró relaciones "
                    f"registradas para {source_name}."
                )

            return (
                f"Relaciones verificadas para "
                f"{source_name}:\n"
                + "\n".join(
                    f"- {entry}"
                    for entry in entries
                )
            )

        names = []

        for row in rows:

            if not isinstance(
                row,
                dict,
            ):
                continue

            name = (
                row.get(
                    "name"
                )
                or row.get(
                    "asset_id"
                )
            )

            if (
                name
                and name not in names
            ):

                names.append(
                    name
                )

        if relationship == "DEPENDS_ON":

            if not names:

                return (
                    "ATLAS no registra dependencias "
                    f"DEPENDS_ON para {source_name}."
                )

            return (
                f"{source_name} depende de: "
                + ", ".join(
                    names
                )
                + "."
            )

        if not names:

            return (
                "ATLAS no encontró relaciones "
                f"{relationship} para {source_name}."
            )

        return (
            f"Relaciones {relationship} "
            f"verificadas para {source_name}: "
            + ", ".join(
                names
            )
            + "."
        )


    def run(
        self,
        user_request,
    ):

        self._emit(
            "semantic_started",
            query=user_request,
        )

        semantic = (
            self._semantic_fast_path(
                user_request
            )
        )

        if semantic is not None:

            self._emit(
                "semantic_completed",
                status="SUCCESS",
                mode="deterministic",
                tools_used=list(
                    semantic.get(
                        "tools_used",
                        [],
                    )
                    or []
                ),
            )

            self._emit(
                "answer_ready",
                status="SUCCESS",
                llm_used=False,
            )

            return semantic

        self._emit(
            "semantic_completed",
            status="MISS",
        )


        self._emit(
            "tool_preflight_started",
        )

        tool = (
            self._tool_fast_path(
                user_request
            )
        )

        if tool is not None:

            self._emit(
                "tool_preflight_completed",
                status="SUCCESS",
                tools_used=list(
                    tool.get(
                        "tools_used",
                        [],
                    )
                    or []
                ),
            )

            self._emit(
                "answer_ready",
                status="SUCCESS",
                llm_used=False,
            )

            return tool

        self._emit(
            "tool_preflight_completed",
            status="MISS",
        )

        observations = []

        planner_model = None
        planner_provider = None

        tools_used = []

        for step in range(
            1,
            self.max_steps + 1,
        ):

            prompt = self._build_prompt(
                user_request,
                observations,
            )

            response = self._ask_planner(
                self.ai_request(
                    prompt
                )
            )

            planner_model = (
                response.model
            )

            planner_provider = (
                response.provider
            )

            try:

                decision = (
                    self._parse_response(
                        response.content
                    )
                )

            except ValueError as exc:

                return {
                    "status":
                        "ERROR",

                    "error":
                        str(exc),

                    "answer":
                        (
                            "ATLAS could not parse "
                            "the knowledge-agent decision."
                        ),

                    "steps":
                        step,

                    "model":
                        planner_model,

                    "provider":
                        planner_provider,

                    "llm_used":
                        True,

                    "tools_used":
                        tools_used,

                    "observations":
                        observations,
                }

            action = decision.get(
                "action"
            )

            if action == "final":

                self._emit(
                    "answer_ready",
                    status="SUCCESS",
                    step=step,
                    llm_used=True,
                )

                return {
                    "status":
                        "SUCCESS",

                    "answer":
                        decision.get(
                            "answer",
                            "",
                        ),

                    "steps":
                        step,

                    "model":
                        planner_model,

                    "provider":
                        planner_provider,

                    "llm_used":
                        True,

                    "tools_used":
                        tools_used,

                    "observations":
                        observations,
                }

            if action != "tool":

                return {
                    "status":
                        "ERROR",

                    "error":
                        (
                            "Invalid agent action: "
                            f"{action}"
                        ),

                    "answer":
                        (
                            "ATLAS knowledge agent "
                            "returned an invalid action."
                        ),

                    "steps":
                        step,

                    "model":
                        planner_model,

                    "provider":
                        planner_provider,

                    "llm_used":
                        True,

                    "tools_used":
                        tools_used,

                    "observations":
                        observations,
                }

            tool_name = decision.get(
                "tool"
            )

            arguments = decision.get(
                "arguments",
                {},
            )

            if not isinstance(
                arguments,
                dict,
            ):
                arguments = {}

            allowed_tools = {
                tool["name"]
                for tool in self._tool_descriptions()
            }

            if tool_name not in allowed_tools:

                return {
                    "status":
                        "ERROR",

                    "error":
                        (
                            "Agent attempted "
                            "unauthorized tool: "
                            f"{tool_name}"
                        ),

                    "answer":
                        (
                            "ATLAS blocked an unauthorized "
                            "knowledge tool request."
                        ),

                    "steps":
                        step,

                    "model":
                        planner_model,

                    "provider":
                        planner_provider,

                    "llm_used":
                        True,

                    "tools_used":
                        tools_used,

                    "observations":
                        observations,
                }

            print(
                "[AI MCP AGENT] "
                f"step={step} "
                f"tool={tool_name} "
                f"arguments="
                + json.dumps(
                    arguments,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )

            self._emit(
                "tool_started",
                step=step,
                tool=tool_name,
                arguments=arguments,
            )

            tool_started = (
                time.perf_counter()
            )

            result = self._execute_tool(
                tool_name,
                arguments,
            )

            tool_latency_ms = (
                time.perf_counter()
                - tool_started
            ) * 1000

            self._emit(
                "tool_completed",
                step=step,
                tool=tool_name,
                status=(
                    "SUCCESS"
                    if result.success
                    else "ERROR"
                ),
                latency_ms=round(
                    tool_latency_ms,
                    2,
                ),
                evidence=list(
                    result.evidence
                    or []
                ),
            )

            tools_used.append(
                tool_name
            )

            observation = {
                "step":
                    step,

                "tool":
                    tool_name,

                "arguments":
                    arguments,

                "status":
                    (
                        "SUCCESS"
                        if result.success
                        else "ERROR"
                    ),

                "result":
                    result.data,

                "error":
                    result.error,

                "evidence":
                    result.evidence,
            }

            observations.append(
                observation
            )

            if (
                tool_name
                == "atlas_query_relations"
            ):

                verified_answer = (
                    self._verified_relation_answer(
                        arguments,
                        result,
                    )
                )

                if (
                    verified_answer
                    is not None
                ):

                    print(
                        "[AI MCP AGENT] "
                        "verified_relation_synthesis=true"
                    )

                    self._emit(
                        "answer_ready",
                        status="SUCCESS",
                        step=step,
                        llm_used=True,
                        synthesis=(
                            "verified_relation"
                        ),
                    )

                    return {
                        "status":
                            "SUCCESS",

                        "answer":
                            verified_answer,

                        "steps":
                            step,

                        "model":
                            planner_model,

                        "provider":
                            planner_provider,

                        "llm_used":
                            True,

                        "tools_used":
                            tools_used,

                        "observations":
                            observations,
                    }

        return {
            "status":
                "MAX_STEPS",

            "answer":
                (
                    "Investigation stopped because "
                    f"the maximum of {self.max_steps} "
                    "steps was reached."
                ),

            "steps":
                self.max_steps,

            "model":
                planner_model,

            "provider":
                planner_provider,

            "llm_used":
                True,

            "tools_used":
                tools_used,

            "observations":
                observations,
        }


    def ai_request(
        self,
        prompt,
    ):

        from atlas.services.ai.models import (
            AIRequest,
        )

        return AIRequest(
            task="reasoning",
            user_prompt=prompt,
            temperature=0,
            max_tokens=500,

            # Critical:
            # this is an agent protocol prompt, not infrastructure
            # context. AIService must not attach the full homelab.
            context_required=False,
        )

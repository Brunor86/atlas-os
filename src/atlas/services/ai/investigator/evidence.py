from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)

from atlas.services.ai.investigator.contracts import (
    AttentionFact,
    RelationFact,
    StatusFact,
    StatusQueryFact,
    VerifiedFact,
)


@dataclass
class EvidenceLedger:
    """
    Convert ATLAS tool evidence into canonical verified facts.

    The ledger is framework-agnostic:

        MCP result / native tool result
                    ->
              EvidenceLedger
                    ->
              VerifiedFact

    It contains no LLM, Ollama, PydanticAI or routing logic.
    """

    facts: dict[
        str,
        VerifiedFact,
    ] = field(
        default_factory=dict
    )

    index: dict[
        tuple[str, ...],
        str,
    ] = field(
        default_factory=dict
    )

    tool_calls: list[str] = field(
        default_factory=list
    )


    def record_tool_call(
        self,
        name: str,
    ) -> None:

        self.tool_calls.append(
            name
        )


    def _next_id(
        self,
    ) -> str:

        return (
            f"FACT-{len(self.facts) + 1:03d}"
        )


    def _add_relation(
        self,
        *,
        subject_id: str,
        subject_name: str | None,
        predicate: str,
        object_id: str,
        object_name: str | None,
        confidence: float,
        source_tool: str,
        evidence: list[str],
    ) -> str:

        key = (
            "RELATION",
            subject_id,
            predicate,
            object_id,
        )

        existing = self.index.get(
            key
        )

        if existing:
            return existing

        fact_id = self._next_id()

        fact = RelationFact(
            id=fact_id,
            subject_id=subject_id,
            subject_name=subject_name,
            predicate=predicate,
            object_id=object_id,
            object_name=object_name,
            confidence=confidence,
            source_tool=source_tool,
            evidence=evidence,
        )

        self.facts[
            fact_id
        ] = fact

        self.index[
            key
        ] = fact_id

        return fact_id


    def _add_attention(
        self,
        *,
        signal_kind: str,
        signal_id: str,
        asset_id: str | None,
        severity: str,
        status: str,
        title: str,
        message: str,
        category: str | None,
        source: str | None,
        last_seen: str | None,
        source_tool: str,
    ) -> str:

        key = (
            "ATTENTION",
            signal_kind,
            signal_id,
            asset_id or "",
        )

        existing = self.index.get(
            key
        )

        if existing:
            return existing

        fact_id = self._next_id()

        fact = AttentionFact(
            id=fact_id,
            signal_kind=signal_kind,
            signal_id=signal_id,
            asset_id=asset_id,
            severity=severity,
            status=status,
            title=title,
            message=message,
            category=category,
            source=source,
            last_seen=last_seen,
            source_tool=source_tool,
        )

        self.facts[
            fact_id
        ] = fact

        self.index[
            key
        ] = fact_id

        return fact_id


    def _add_status_query(
        self,
        *,
        complete: bool,
        count: int,
        status_filter: str | None,
        asset_type: str | None,
        criticality: str | None,
        role: str | None,
        source_tool: str,
        evidence: list[str],
    ) -> str:

        key = (
            "STATUS_QUERY",
            str(
                complete
            ),
            str(
                count
            ),
            status_filter or "",
            asset_type or "",
            criticality or "",
            role or "",
        )

        existing = self.index.get(
            key
        )

        if existing:
            return existing

        fact_id = self._next_id()

        fact = StatusQueryFact(
            id=fact_id,
            complete=complete,
            count=count,
            status_filter=status_filter,
            asset_type=asset_type,
            criticality=criticality,
            role=role,
            source_tool=source_tool,
            evidence=evidence,
        )

        self.facts[
            fact_id
        ] = fact

        self.index[
            key
        ] = fact_id

        return fact_id


    def _add_status(
        self,
        *,
        query_fact_id: str,
        asset_id: str,
        asset_name: str | None,
        asset_type: str,
        status: str,
        health: float | None,
        criticality: str | None,
        roles: list[str],
        last_seen: str | None,
        source_tool: str,
        evidence: list[str],
    ) -> str:

        key = (
            "STATUS",
            query_fact_id,
            asset_id,
            status,
        )

        existing = self.index.get(
            key
        )

        if existing:
            return existing

        fact_id = self._next_id()

        fact = StatusFact(
            id=fact_id,
            query_fact_id=query_fact_id,
            asset_id=asset_id,
            asset_name=asset_name,
            asset_type=asset_type,
            status=status,
            health=health,
            criticality=criticality,
            roles=roles,
            last_seen=last_seen,
            source_tool=source_tool,
            evidence=evidence,
        )

        self.facts[
            fact_id
        ] = fact

        self.index[
            key
        ] = fact_id

        return fact_id


    @staticmethod
    def _json_object(
        result,
    ) -> dict:

        if isinstance(
            result,
            dict,
        ):
            return result

        model_dump = getattr(
            result,
            "model_dump",
            None,
        )

        if callable(
            model_dump
        ):

            value = model_dump(
                mode="json"
            )

            if isinstance(
                value,
                dict,
            ):
                return value

        return {}


    @classmethod
    def _atlas_data(
        cls,
        result,
    ) -> dict:

        raw = cls._json_object(
            result
        )

        data = raw.get(
            "data"
        )

        if isinstance(
            data,
            dict,
        ):
            return data

        return raw


    def ingest(
        self,
        tool_name: str,
        result,
    ) -> list[str]:

        data = self._atlas_data(
            result
        )

        if (
            data.get(
                "status"
            )
            != "SUCCESS"
        ):
            return []

        fact_ids = []

        # ----------------------------------------------------------
        # SEMANTIC RELATIONSHIPS
        # ----------------------------------------------------------

        if (
            tool_name
            == "atlas_query_entity_relations"
        ):

            for item in data.get(
                "results",
                [],
            ):

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                subject_id = str(
                    item.get(
                        "source_asset_id"
                    )
                    or ""
                ).strip()

                object_id = str(
                    item.get(
                        "target_asset_id"
                    )
                    or ""
                ).strip()

                predicate = str(
                    item.get(
                        "relationship"
                    )
                    or ""
                ).strip().upper()

                if (
                    not subject_id
                    or not object_id
                    or not predicate
                ):
                    continue

                fact_ids.append(
                    self._add_relation(
                        subject_id=subject_id,
                        subject_name=(
                            item.get(
                                "source_name"
                            )
                        ),
                        predicate=predicate,
                        object_id=object_id,
                        object_name=(
                            item.get(
                                "target_name"
                            )
                        ),
                        confidence=float(
                            item.get(
                                "confidence",
                                0.0,
                            )
                            or 0.0
                        ),
                        source_tool=tool_name,
                        evidence=list(
                            item.get(
                                "evidence",
                                [],
                            )
                            or []
                        ),
                    )
                )

        # ----------------------------------------------------------
        # CURRENT OPERATIONAL ATTENTION
        # ----------------------------------------------------------

        elif (
            tool_name
            == "atlas_attention_summary"
        ):

            attention = data.get(
                "attention"
            )

            if isinstance(
                attention,
                dict,
            ):

                for item in attention.get(
                    "items",
                    [],
                ):

                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    signal_id = str(
                        item.get(
                            "id"
                        )
                        or ""
                    ).strip()

                    if not signal_id:
                        continue

                    fact_ids.append(
                        self._add_attention(
                            signal_kind=str(
                                item.get(
                                    "kind"
                                )
                                or "UNKNOWN"
                            ).strip().upper(),
                            signal_id=signal_id,
                            asset_id=(
                                str(
                                    item.get(
                                        "asset_id"
                                    )
                                ).strip()
                                if item.get(
                                    "asset_id"
                                )
                                is not None
                                else None
                            ),
                            severity=str(
                                item.get(
                                    "severity"
                                )
                                or "UNKNOWN"
                            ).strip().upper(),
                            status=str(
                                item.get(
                                    "status"
                                )
                                or "UNKNOWN"
                            ).strip().upper(),
                            title=str(
                                item.get(
                                    "title"
                                )
                                or "Operational signal"
                            ).strip(),
                            message=str(
                                item.get(
                                    "message"
                                )
                                or ""
                            ).strip(),
                            category=(
                                str(
                                    item.get(
                                        "category"
                                    )
                                ).strip()
                                if item.get(
                                    "category"
                                )
                                is not None
                                else None
                            ),
                            source=(
                                str(
                                    item.get(
                                        "source"
                                    )
                                ).strip()
                                if item.get(
                                    "source"
                                )
                                is not None
                                else None
                            ),
                            last_seen=(
                                str(
                                    item.get(
                                        "last_seen"
                                    )
                                ).strip()
                                if item.get(
                                    "last_seen"
                                )
                                is not None
                                else None
                            ),
                            source_tool=tool_name,
                        )
                    )

        # ----------------------------------------------------------
        # CANONICAL ASSET STATUS
        # ----------------------------------------------------------

        elif (
            tool_name
            == "atlas_query_asset_status"
        ):

            complete = bool(
                data.get(
                    "complete"
                )
            )

            filters = data.get(
                "filters"
            )

            if not isinstance(
                filters,
                dict,
            ):
                filters = {}

            assets = data.get(
                "assets"
            )

            if not isinstance(
                assets,
                list,
            ):
                assets = []

            try:

                declared_count = int(
                    data.get(
                        "count",
                        len(
                            assets
                        ),
                    )
                )

            except (
                TypeError,
                ValueError,
            ):

                return []

            if (
                declared_count < 0
                or declared_count
                != len(
                    assets
                )
            ):

                return []

            query_evidence = list(
                data.get(
                    "evidence",
                    [],
                )
                or []
            )

            query_fact_id = (
                self._add_status_query(
                    complete=complete,
                    count=declared_count,
                    status_filter=(
                        str(
                            filters.get(
                                "status"
                            )
                        ).strip().upper()
                        if filters.get(
                            "status"
                        )
                        is not None
                        else None
                    ),
                    asset_type=(
                        str(
                            filters.get(
                                "asset_type"
                            )
                        ).strip().upper()
                        if filters.get(
                            "asset_type"
                        )
                        is not None
                        else None
                    ),
                    criticality=(
                        str(
                            filters.get(
                                "criticality"
                            )
                        ).strip().upper()
                        if filters.get(
                            "criticality"
                        )
                        is not None
                        else None
                    ),
                    role=(
                        str(
                            filters.get(
                                "role"
                            )
                        ).strip().upper()
                        if filters.get(
                            "role"
                        )
                        is not None
                        else None
                    ),
                    source_tool=tool_name,
                    evidence=query_evidence,
                )
            )

            fact_ids.append(
                query_fact_id
            )

            for item in assets:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                asset_id = str(
                    item.get(
                        "id"
                    )
                    or ""
                ).strip()

                asset_type = str(
                    item.get(
                        "type"
                    )
                    or ""
                ).strip().upper()

                asset_status = str(
                    item.get(
                        "status"
                    )
                    or ""
                ).strip().upper()

                if (
                    not asset_id
                    or not asset_type
                    or not asset_status
                ):
                    continue

                health = item.get(
                    "health"
                )

                if health is not None:

                    try:
                        health = float(
                            health
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        health = None

                roles = item.get(
                    "roles"
                )

                if not isinstance(
                    roles,
                    list,
                ):
                    roles = []

                fact_ids.append(
                    self._add_status(
                        query_fact_id=query_fact_id,
                        asset_id=asset_id,
                        asset_name=(
                            str(
                                item.get(
                                    "name"
                                )
                            ).strip()
                            if item.get(
                                "name"
                            )
                            is not None
                            else None
                        ),
                        asset_type=asset_type,
                        status=asset_status,
                        health=health,
                        criticality=(
                            str(
                                item.get(
                                    "criticality"
                                )
                            ).strip().upper()
                            if item.get(
                                "criticality"
                            )
                            is not None
                            else None
                        ),
                        roles=[
                            str(
                                role
                            ).strip().upper()
                            for role in roles
                            if str(
                                role
                            ).strip()
                        ],
                        last_seen=(
                            str(
                                item.get(
                                    "last_seen"
                                )
                            ).strip()
                            if item.get(
                                "last_seen"
                            )
                            is not None
                            else None
                        ),
                        source_tool=tool_name,
                        evidence=query_evidence,
                    )
                )

        return fact_ids


    def validate_fact_ids(
        self,
        fact_ids: list[str],
    ) -> list[str]:

        return [
            fact_id
            for fact_id in fact_ids
            if fact_id not in self.facts
        ]


    def selected(
        self,
        fact_ids: list[str],
    ) -> list[VerifiedFact]:

        result = []

        seen = set()

        for fact_id in fact_ids:

            if fact_id in seen:
                continue

            seen.add(
                fact_id
            )

            fact = self.facts.get(
                fact_id
            )

            if fact is not None:
                result.append(
                    fact
                )

        return result

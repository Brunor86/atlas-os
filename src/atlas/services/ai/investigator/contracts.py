from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)


class RelationFact(BaseModel):
    """
    Canonical relationship verified by ATLAS evidence.

    Relationship direction always follows the canonical graph:

        subject -> predicate -> object
    """

    id: str

    kind: Literal[
        "RELATION"
    ] = "RELATION"

    subject_id: str
    subject_name: str | None = None

    predicate: str

    object_id: str
    object_name: str | None = None

    confidence: float = 0.0

    source_tool: str

    evidence: list[str] = Field(
        default_factory=list
    )


class AttentionFact(BaseModel):
    """
    Current operational signal verified by ATLAS.
    """

    id: str

    kind: Literal[
        "ATTENTION"
    ] = "ATTENTION"

    signal_kind: str
    signal_id: str

    asset_id: str | None = None

    severity: str
    status: str

    title: str
    message: str = ""

    category: str | None = None
    source: str | None = None
    last_seen: str | None = None

    source_tool: str


class StatusQueryFact(BaseModel):
    """
    Verified execution of a structured ATLAS status inventory query.

    This fact exists even when zero assets match.

    Therefore:

        complete=True
        count=0

    is verified negative evidence, not missing evidence.
    """

    id: str

    kind: Literal[
        "STATUS_QUERY"
    ] = "STATUS_QUERY"

    complete: bool

    count: int = Field(
        ge=0
    )

    status_filter: str | None = None
    asset_type: str | None = None
    criticality: str | None = None
    role: str | None = None

    source_tool: str

    evidence: list[str] = Field(
        default_factory=list
    )


class StatusFact(BaseModel):
    """
    Current canonical status of one ATLAS asset returned by a verified
    structured status query.
    """

    id: str

    kind: Literal[
        "STATUS"
    ] = "STATUS"

    query_fact_id: str

    asset_id: str
    asset_name: str | None = None

    asset_type: str

    status: str

    health: float | None = None

    criticality: str | None = None

    roles: list[str] = Field(
        default_factory=list
    )

    last_seen: str | None = None

    source_tool: str

    evidence: list[str] = Field(
        default_factory=list
    )


VerifiedFact = (
    RelationFact
    | AttentionFact
    | StatusQueryFact
    | StatusFact
)


class InvestigationReport(BaseModel):
    """
    Final evidence selection produced by an investigator.

    The investigator selects verified ATLAS fact identifiers.
    It does not author new authoritative infrastructure facts.
    """

    status: Literal[
        "ANSWERED",
        "INSUFFICIENT_EVIDENCE",
    ]

    fact_ids: list[str] = Field(
        default_factory=list
    )

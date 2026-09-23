from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SemanticEntityKind(str, Enum):

    ASSET = "ASSET"
    GROUP = "GROUP"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"


@dataclass(
    frozen=True,
    slots=True,
)
class SemanticGroup:
    """
    Technology-neutral logical grouping discovered by a provider.

    Providers translate their own native concepts into this contract.

    Examples of provider-side mappings:

        Docker Compose project
            -> application_stack

        Kubernetes namespace/deployment
            -> application_stack

        virtualization cluster
            -> infrastructure_cluster

    Consumers never need to understand the original technology.
    """

    kind: str
    value: str

    scope: str | None = None
    source: str | None = None

    confidence: float = 1.0

    def as_dict(self) -> dict:

        return {
            "kind":
                self.kind,

            "value":
                self.value,

            "scope":
                self.scope,

            "source":
                self.source,

            "confidence":
                self.confidence,
        }


@dataclass(
    slots=True,
)
class ResolvedSemanticEntity:

    query: str

    kind: SemanticEntityKind

    asset_id: str | None = None

    member_ids: list[str] = field(
        default_factory=list
    )

    group_kind: str | None = None
    group_value: str | None = None
    group_scope: str | None = None

    confidence: float = 0.0

    evidence: list[str] = field(
        default_factory=list
    )

    candidates: list[dict] = field(
        default_factory=list
    )

    @property
    def resolved(self) -> bool:

        return self.kind in {
            SemanticEntityKind.ASSET,
            SemanticEntityKind.GROUP,
        }

    @property
    def reference(self) -> str | None:

        if self.kind == SemanticEntityKind.ASSET:

            return self.asset_id

        if (
            self.kind
            == SemanticEntityKind.GROUP
        ):

            parts = [
                "group",
                self.group_kind or "unknown",
                self.group_scope or "global",
                self.group_value or "unknown",
            ]

            return ":".join(
                str(part)
                for part in parts
            )

        return None

    def as_dict(self) -> dict:

        return {
            "query":
                self.query,

            "kind":
                self.kind.value,

            "reference":
                self.reference,

            "asset_id":
                self.asset_id,

            "member_ids":
                list(
                    self.member_ids
                ),

            "group_kind":
                self.group_kind,

            "group_value":
                self.group_value,

            "group_scope":
                self.group_scope,

            "confidence":
                self.confidence,

            "evidence":
                list(
                    self.evidence
                ),

            "candidates":
                list(
                    self.candidates
                ),
        }

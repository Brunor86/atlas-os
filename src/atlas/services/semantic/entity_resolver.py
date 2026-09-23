from __future__ import annotations

import unicodedata

from atlas.core.semantic import (
    ResolvedSemanticEntity,
    SemanticEntityKind,
)

from atlas.services.knowledge.asset_resolver import (
    AssetResolver,
)


class SemanticEntityResolver:
    """
    Resolve language-level entities without product knowledge.

    Resolution order:

        1. exact asset id
        2. exact asset name
        3. exact discovered semantic group
        4. existing canonical asset fallback
        5. not found

    Important:

    A semantic group is discovered by providers and represented by
    the generic metadata contract `semantic_groups`.

    This resolver has no knowledge of Docker Compose, Kubernetes,
    Proxmox, Immich, Jellyfin, or any other concrete technology or
    application.
    """

    def __init__(
        self,
        registry,
        *,
        asset_resolver=None,
    ):

        self.registry = registry

        self.asset_resolver = (
            asset_resolver
            or AssetResolver(
                registry
            )
        )


    @staticmethod
    def _normalize(
        value,
    ) -> str:

        value = unicodedata.normalize(
            "NFKD",
            str(
                value or ""
            ),
        )

        value = "".join(
            char
            for char in value
            if not unicodedata.combining(
                char
            )
        )

        return (
            value
            .strip()
            .casefold()
        )


    @staticmethod
    def _group_reference(
        group,
    ) -> str:

        parts = [
            "group",
            group.get(
                "kind"
            ) or "unknown",
            group.get(
                "scope"
            ) or "global",
            group.get(
                "value"
            ) or "unknown",
        ]

        return ":".join(
            str(part)
            for part in parts
        )


    def _semantic_groups(
        self,
    ):

        groups = {}

        for asset in self.registry.assets():

            metadata = (
                getattr(
                    asset,
                    "metadata",
                    {},
                )
                or {}
            )

            memberships = (
                metadata.get(
                    "semantic_groups"
                )
                or []
            )

            if not isinstance(
                memberships,
                list,
            ):
                continue

            for membership in memberships:

                if not isinstance(
                    membership,
                    dict,
                ):
                    continue

                kind = str(
                    membership.get(
                        "kind",
                        ""
                    )
                ).strip()

                value = str(
                    membership.get(
                        "value",
                        ""
                    )
                ).strip()

                scope = membership.get(
                    "scope"
                )

                source = membership.get(
                    "source"
                )

                confidence = float(
                    membership.get(
                        "confidence",
                        1.0,
                    )
                    or 0.0
                )

                if (
                    not kind
                    or not value
                ):
                    continue

                key = (
                    self._normalize(
                        kind
                    ),
                    self._normalize(
                        value
                    ),
                    self._normalize(
                        scope
                    ),
                )

                item = groups.setdefault(
                    key,
                    {
                        "kind":
                            kind,

                        "value":
                            value,

                        "scope":
                            scope,

                        "sources":
                            set(),

                        "confidence":
                            confidence,

                        "member_ids":
                            [],
                    },
                )

                if source:
                    item[
                        "sources"
                    ].add(
                        str(source)
                    )

                item[
                    "confidence"
                ] = max(
                    item[
                        "confidence"
                    ],
                    confidence,
                )

                if (
                    asset.id
                    not in item[
                        "member_ids"
                    ]
                ):
                    item[
                        "member_ids"
                    ].append(
                        asset.id
                    )

        return groups


    def resolve(
        self,
        query: str,
    ) -> ResolvedSemanticEntity:

        original = str(
            query or ""
        ).strip()

        needle = self._normalize(
            original
        )

        if not needle:

            return ResolvedSemanticEntity(
                query=original,
                kind=(
                    SemanticEntityKind
                    .NOT_FOUND
                ),
                confidence=0.0,
                evidence=[
                    "empty semantic entity query",
                ],
            )

        assets = list(
            self.registry.assets()
        )

        semantic_groups = (
            self._semantic_groups()
        )

        # ----------------------------------------------------------
        # 1. EXACT ASSET ID
        # ----------------------------------------------------------

        exact_id = self.registry.get(
            original
        )

        if exact_id is not None:

            return ResolvedSemanticEntity(
                query=original,
                kind=(
                    SemanticEntityKind
                    .ASSET
                ),
                asset_id=exact_id.id,
                member_ids=[
                    exact_id.id
                ],
                confidence=1.0,
                evidence=[
                    "exact asset id",
                ],
            )

        # ----------------------------------------------------------
        # 2. EXACT CANONICAL SEMANTIC GROUP REFERENCE
        #
        # References emitted by ResolvedSemanticEntity.reference are
        # intentionally valid semantic inputs. Consumers may therefore
        # resolve once and safely reuse the canonical reference.
        # ----------------------------------------------------------

        for group in (
            semantic_groups.values()
        ):

            reference = (
                self._group_reference(
                    group
                )
            )

            if (
                self._normalize(
                    reference
                )
                != needle
            ):
                continue

            sources = sorted(
                group[
                    "sources"
                ]
            )

            return ResolvedSemanticEntity(
                query=original,
                kind=(
                    SemanticEntityKind
                    .GROUP
                ),
                member_ids=list(
                    group[
                        "member_ids"
                    ]
                ),
                group_kind=group[
                    "kind"
                ],
                group_value=group[
                    "value"
                ],
                group_scope=group[
                    "scope"
                ],
                confidence=group[
                    "confidence"
                ],
                evidence=[
                    (
                        "canonical semantic "
                        "group reference"
                    ),
                    (
                        "sources: "
                        + ", ".join(
                            sources
                        )
                        if sources
                        else (
                            "provider semantic "
                            "group"
                        )
                    ),
                ],
            )

        # ----------------------------------------------------------
        # 3. EXACT ASSET NAME
        #
        # AssetResolver remains responsible for choosing the
        # canonical representation when several assets share the
        # same exact infrastructure name.
        # ----------------------------------------------------------

        exact_names = [
            asset
            for asset in assets
            if self._normalize(
                getattr(
                    asset,
                    "name",
                    "",
                )
            )
            == needle
        ]

        if exact_names:

            asset = (
                self.asset_resolver
                .resolve(
                    original
                )
            )

            if asset is not None:

                return ResolvedSemanticEntity(
                    query=original,
                    kind=(
                        SemanticEntityKind
                        .ASSET
                    ),
                    asset_id=asset.id,
                    member_ids=[
                        asset.id
                    ],
                    confidence=1.0,
                    evidence=[
                        "exact asset name",
                        (
                            "canonical asset "
                            "resolution"
                        ),
                    ],
                )

        # ----------------------------------------------------------
        # 3. EXACT DISCOVERED SEMANTIC GROUP
        # ----------------------------------------------------------

        matches = []

        for group in (
            semantic_groups.values()
        ):

            if (
                self._normalize(
                    group[
                        "value"
                    ]
                )
                != needle
            ):
                continue

            matches.append(
                group
            )

        if len(matches) == 1:

            group = matches[0]

            sources = sorted(
                group[
                    "sources"
                ]
            )

            return ResolvedSemanticEntity(
                query=original,
                kind=(
                    SemanticEntityKind
                    .GROUP
                ),
                member_ids=list(
                    group[
                        "member_ids"
                    ]
                ),
                group_kind=group[
                    "kind"
                ],
                group_value=group[
                    "value"
                ],
                group_scope=group[
                    "scope"
                ],
                confidence=group[
                    "confidence"
                ],
                evidence=[
                    (
                        "discovered semantic "
                        "group"
                    ),
                    (
                        "sources: "
                        + ", ".join(
                            sources
                        )
                        if sources
                        else (
                            "provider semantic "
                            "group"
                        )
                    ),
                ],
            )

        if len(matches) > 1:

            return ResolvedSemanticEntity(
                query=original,
                kind=(
                    SemanticEntityKind
                    .AMBIGUOUS
                ),
                confidence=max(
                    group[
                        "confidence"
                    ]
                    for group in matches
                ),
                evidence=[
                    (
                        "multiple discovered "
                        "semantic groups match"
                    ),
                ],
                candidates=[
                    {
                        "kind":
                            group[
                                "kind"
                            ],

                        "value":
                            group[
                                "value"
                            ],

                        "scope":
                            group[
                                "scope"
                            ],

                        "member_ids":
                            list(
                                group[
                                    "member_ids"
                                ]
                            ),
                    }
                    for group in matches
                ],
            )

        # ----------------------------------------------------------
        # 4. EXISTING CANONICAL FALLBACK
        #
        # This preserves current partial identity behavior only
        # AFTER exact semantic groups have had a chance to resolve.
        #
        # Therefore:
        #
        #   "nebula"
        #
        # resolves a discovered group named nebula before an asset
        # such as nebula-worker happens to win a partial-name race.
        # ----------------------------------------------------------

        asset = (
            self.asset_resolver
            .resolve(
                original
            )
        )

        if asset is not None:

            return ResolvedSemanticEntity(
                query=original,
                kind=(
                    SemanticEntityKind
                    .ASSET
                ),
                asset_id=asset.id,
                member_ids=[
                    asset.id
                ],
                confidence=0.70,
                evidence=[
                    (
                        "canonical asset "
                        "fallback"
                    ),
                ],
            )

        return ResolvedSemanticEntity(
            query=original,
            kind=(
                SemanticEntityKind
                .NOT_FOUND
            ),
            confidence=0.0,
            evidence=[
                "no asset or semantic group matched",
            ],
        )

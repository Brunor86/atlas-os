"""
Retired compatibility module.

Canonical impact analysis is provided by:

    atlas.services.noc.impact.ImpactEngine

and traversal semantics are provided by:

    atlas.services.assets.topology_traversal.TopologyTraversalService

This module intentionally contains no independent traversal logic.
"""

from atlas.services.noc.impact import ImpactEngine


class RecursiveImpactEngine:
    """
    Compatibility facade for historical imports.

    New code must use ImpactEngine directly.
    """

    def __init__(self, cards=None):
        self.cards = cards or []
        self.engine = ImpactEngine()

    def analyze(
        self,
        dependency,
        depth=3,
    ):
        result = self.engine.analyze(
            dependency
        )

        if not result or "error" in result:
            return []

        return result.get(
            "downstream",
            [],
        )

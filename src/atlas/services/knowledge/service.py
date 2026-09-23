import logging

from atlas.services.assets.registry import AssetRegistry
from atlas.services.assets.runtime import get_asset_registry
from atlas.services.knowledge.engine import KnowledgeEngine
from atlas.services.knowledge.intelligence import KnowledgeIntelligenceAnalyzer



logger = logging.getLogger(__name__)


def _diagnostic(*parts):

    message = " ".join(
        str(part)
        for part in parts
    )

    if "ERROR" in message.upper():

        logger.warning(
            "%s",
            message,
        )

    else:

        logger.debug(
            "%s",
            message,
        )


class KnowledgeService:


    def __init__(
        self,
        registry: AssetRegistry,
    ):

        self.registry = registry or get_asset_registry()

        self.engine = None

        self.intelligence = KnowledgeIntelligenceAnalyzer()

        self.cards = []



    def _ensure_loaded(self):

        if self.engine is not None:
            return


        _diagnostic("DEBUG KNOWLEDGE BUILD START")

        _diagnostic(
            "DEBUG KNOWLEDGE REGISTRY ID:",
            id(self.registry)
        )


        _diagnostic(
            "DEBUG KNOWLEDGE ASSETS BEFORE DISCOVER:",
            len(self.registry.assets())
        )


        if not self.registry.assets():

            _diagnostic(
                "DEBUG KNOWLEDGE FALLBACK DISCOVERY"
            )

            try:
                from atlas.services.discovery.kernel import DiscoveryKernel

                DiscoveryKernel().discover()

            except Exception as e:

                _diagnostic(
                    "DEBUG KNOWLEDGE DISCOVERY ERROR:",
                    e
                )


        _diagnostic(
            "DEBUG KNOWLEDGE ASSETS AFTER DISCOVER:",
            len(self.registry.assets())
        )


        self.engine = KnowledgeEngine(
        self.registry
    )

        self.cards = []


        for asset in self.registry.assets():

            card = self.engine.build(
                asset
            )


            self.intelligence.analyze(
                card
            )


            self.cards.append(
                card
            )


        _diagnostic(
            "DEBUG KNOWLEDGE BUILD END",
            len(self.cards)
        )


    def _build(self):

        self._ensure_loaded()



    def impact(
        self,
        dependency,
    ):

        self._ensure_loaded()


        # -----------------------------------------------------------------
        # Compatibility projection
        #
        # Canonical impact semantics now live in:
        #
        #   ImpactEngine
        #       -> TopologyTraversalService
        #
        # KnowledgeService historically exposed impact() through
        # RecursiveImpactEngine. Keep the public method temporarily, but
        # delegate to the canonical engine instead of maintaining a second
        # traversal implementation.
        # -----------------------------------------------------------------

        from atlas.services.noc.impact import ImpactEngine

        engine = ImpactEngine()

        result = engine.analyze(
            dependency
        )

        if not result or "error" in result:
            return []

        projected = []

        for item in result.get(
            "downstream",
            [],
        ):

            asset_id = item.get(
                "asset"
            )

            if not asset_id:
                continue

            asset = self.registry.get(
                asset_id
            )

            if asset is None:
                continue

            try:
                asset_type = asset.type.name
            except Exception:
                asset_type = "UNKNOWN"

            try:
                roles = [
                    role.name
                    for role in asset.asset_roles
                ]
            except Exception:
                roles = []

            projected.append(
                {
                    "asset_id": asset_id,
                    "application": asset.name,
                    "asset_name": asset.name,
                    "asset_type": asset_type,
                    "importance": (
                        getattr(
                            getattr(
                                asset,
                                "service_importance",
                                None,
                            ),
                            "name",
                            "UNKNOWN",
                        )
                    ),
                    "roles": roles,
                    "depth": item.get(
                        "depth",
                        0,
                    ),
                    "reason": item.get(
                        "reason",
                        "Downstream impact",
                    ),
                    "relationship": item.get(
                        "relationship",
                        "",
                    ),
                    "criticality": getattr(
                        getattr(
                            asset,
                            "criticality",
                            None,
                        ),
                        "name",
                        "UNKNOWN",
                    ),
                    "impact_score": item.get(
                        "impact_score",
                        0,
                    ),
                }
            )

        return projected



    def resolve_application(
        self,
        asset_id,
    ):

        self._ensure_loaded()


        for card in self.cards:

            if card.asset_id == asset_id:

                return card.asset_name


        return asset_id


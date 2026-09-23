from dataclasses import dataclass


@dataclass(slots=True)
class AssetReference:
    asset_id: str
    asset_name: str
    confidence: float
    source: str


class AssetReferenceResolver:

    REFERENCE_TERMS = (
        "ese",
        "esa",
        "eso",
        "el anterior",
        "la anterior",
        "ese servidor",
        "ese contenedor",
        "esa aplicación",
        "ese servicio",
    )

    def __init__(self, asset_tools):
        self.asset_tools = asset_tools

    def resolve(
        self,
        prompt: str,
        conversation,
    ) -> AssetReference | None:

        prompt_lower = prompt.lower()

        # 1. Explicit asset mentioned in current prompt.
        matches = self.asset_tools.find_asset(
            prompt
        )

        if (
            matches.status == "SUCCESS"
            and matches.result
            and len(matches.result) == 1
        ):
            asset = matches.result[0]

            return AssetReference(
                asset_id=asset["id"],
                asset_name=asset["name"],
                confidence=1.0,
                source="explicit",
            )

        # 2. Resolve conversational references.
        if self._contains_reference(prompt_lower):

            asset_id = conversation.metadata.get(
                "active_asset_id"
            )

            asset_name = conversation.metadata.get(
                "active_asset_name"
            )

            if asset_id:
                return AssetReference(
                    asset_id=asset_id,
                    asset_name=asset_name or asset_id,
                    confidence=0.95,
                    source="conversation",
                )

        return None

    def remember(
        self,
        conversation,
        reference: AssetReference,
    ):

        conversation.metadata[
            "active_asset_id"
        ] = reference.asset_id

        conversation.metadata[
            "active_asset_name"
        ] = reference.asset_name

    def _contains_reference(
        self,
        prompt: str,
    ) -> bool:

        return any(
            term in prompt
            for term in self.REFERENCE_TERMS
        )

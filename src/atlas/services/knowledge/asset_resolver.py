class AssetResolver:

    def __init__(self, registry=None):

        if registry is not None:
            self._registry = registry

        else:
            from atlas.services.assets.runtime import get_asset_registry
            self._registry = get_asset_registry()


    @property
    def registry(self):

        return self._registry


    def get(self, asset_id):
        """
        Canonical deterministic asset resolution.

        Resolution priority:
        1. Exact registry ID
        2. Exact unique name
        3. Semantic infrastructure host preference
        4. Exact/partial identity
        5. Partial ID/name fallback
        """

        if not asset_id:
            return None

        needle = str(asset_id).strip().lower()

        # --------------------------------------------------------------
        # 1. EXACT ASSET ID
        # --------------------------------------------------------------

        asset = self.registry.get(asset_id)

        if asset is not None:
            return asset

        assets = list(self.registry.assets())

        # --------------------------------------------------------------
        # 2. EXACT NAME MATCH
        # --------------------------------------------------------------

        exact_name = [
            candidate
            for candidate in assets
            if str(getattr(candidate, "name", "")).lower() == needle
        ]

        if len(exact_name) == 1:
            return exact_name[0]

        # --------------------------------------------------------------
        # 3. SEMANTIC HOST PREFERENCE
        #
        # Duplicate infrastructure names are expected:
        #
        #   SERVER workload-host
        #   VM     workload-host
        #
        # For topology / operational reasoning, prefer the asset that
        # actually owns the workload graph.
        # --------------------------------------------------------------

        if exact_name:

            def score(candidate):
                value = 0

                asset_type = getattr(
                    getattr(candidate, "type", None),
                    "name",
                    "",
                )

                roles = {
                    getattr(role, "name", str(role))
                    for role in getattr(
                        candidate,
                        "asset_roles",
                        set(),
                    )
                }

                if asset_type == "VM":
                    value += 100

                if asset_type == "LXC":
                    value += 90

                if asset_type == "SERVER":
                    value += 20

                if "DOCKER_HOST" in roles:
                    value += 50

                if "APPLICATION_SERVER" in roles:
                    value += 20

                if "MEDIA_SERVER" in roles:
                    value += 10

                # Assets with outgoing HOSTS relationships are
                # infrastructure parents / workload hosts.
                for relation in getattr(
                    candidate,
                    "relationships",
                    [],
                ):

                    relationship_type = getattr(
                        relation,
                        "relationship_type",
                        getattr(
                            relation,
                            "type",
                            "",
                        ),
                    )

                    if str(relationship_type).upper() == "HOSTS":
                        value += 40

                return value

            return max(
                exact_name,
                key=score,
            )

        # --------------------------------------------------------------
        # 4. ID / IDENTITY / RUNTIME MATCH
        # --------------------------------------------------------------

        for candidate in assets:

            candidate_id = str(
                getattr(candidate, "id", "")
            ).lower()

            if candidate_id == needle:
                return candidate

            identity = getattr(
                candidate,
                "identity",
                None,
            )

            if identity:

                for value in (
                    getattr(identity, "device", None),
                    getattr(identity, "serial", None),
                    getattr(identity, "model", None),
                    getattr(identity, "vendor", None),
                ):

                    if value and str(value).lower() == needle:
                        return candidate

            metadata = getattr(
                candidate,
                "metadata",
                {},
            ) or {}

            for key in (
                "container_id",
                "docker_id",
                "id",
                "vmid",
            ):

                value = metadata.get(key)

                if value and str(value).lower() == needle:
                    return candidate

        # --------------------------------------------------------------
        # 5. PARTIAL FALLBACK
        # --------------------------------------------------------------

        partial = []

        for candidate in assets:

            candidate_id = str(
                getattr(candidate, "id", "")
            ).lower()

            candidate_name = str(
                getattr(candidate, "name", "")
            ).lower()

            if needle in candidate_id or needle in candidate_name:
                partial.append(candidate)

        if partial:
            return partial[0]

        return None

    def resolve_dependency(
        self,
        dependency: str,
    ):

        if not dependency:
            return None

        dependency = dependency.lower().strip()

        for asset in self.registry.assets():

            # Exact asset id
            if asset.id.lower() == dependency:
                return asset

            # Exact name
            if asset.name.lower() == dependency:
                return asset

            # Partial name
            if dependency in asset.name.lower():
                return asset

            # Identity matching
            identity = getattr(
                asset,
                "identity",
                None
            )

            if identity:

                values = [
                    identity.device,
                    identity.serial,
                    identity.model,
                ]

                for value in values:

                    if value:

                        value = str(
                            value
                        ).lower()

                        if dependency in value:
                            return asset

            # Metadata matching
            metadata = getattr(
                asset,
                "metadata",
                {}
            )

            for key in [
                "container_id",
                "docker_id",
                "id",
            ]:

                value = metadata.get(
                    key
                )

                if value:

                    value = str(
                        value
                    ).lower()

                    if dependency in value:
                        return asset

        return None


    def resolve_docker_id(
        self,
        docker_id: str,
    ):

        if not docker_id:
            return None

        docker_id = docker_id.lower().strip()

        for asset in self.registry.assets():

            asset_id = str(
                asset.id
            ).lower()

            name = str(
                asset.name
            ).lower()

            # Asset ID
            if docker_id in asset_id:
                return asset

            # Name
            if docker_id in name:
                return asset

            # Runtime identity
            runtime = getattr(
                asset,
                "runtime_identity",
                None
            )

            if runtime:

                container_id = getattr(
                    runtime,
                    "container_id",
                    None
                )

                if container_id:

                    if (
                        docker_id
                        in
                        str(
                            container_id
                        ).lower()
                    ):
                        return asset

            # Metadata
            metadata = getattr(
                asset,
                "metadata",
                {}
            )

            for key in [
                "container_id",
                "docker_id",
                "id",
            ]:

                value = metadata.get(
                    key
                )

                if value:

                    if (
                        docker_id
                        in
                        str(
                            value
                        ).lower()
                    ):
                        return asset

        return None


    def describe(
        self,
        asset_id,
    ):

        asset = self.get(
            asset_id
        )

        if not asset:

            return {
                "name": asset_id,
                "type": "UNKNOWN",
                "roles": [],
                "criticality": "UNKNOWN",
            }

        return {

            "name":
                asset.name,

            "type":
                asset.type.name,

            "roles":
                [
                    role.name
                    for role in asset.asset_roles
                ],

            "criticality":
                asset.criticality.name,

        }

    def resolve(
        self,
        asset_id,
    ):
        """
        Canonical public alias for asset resolution.

        Kept intentionally thin so all consumers share the same
        deterministic resolution logic.
        """

        return self.get(
            asset_id
        )

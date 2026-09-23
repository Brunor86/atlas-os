from dataclasses import dataclass
import re
import unicodedata

from atlas.core.asset import AssetRole


@dataclass(frozen=True)
class ApplicationClassification:

    role: AssetRole | None

    confidence: float

    reason: str

    evidence: tuple[str, ...] = ()


class ApplicationClassifier:
    """
    Infer application roles from discovered semantic metadata.

    The classifier knows infrastructure concepts, not installed
    application identities. Evidence may come from:

    - OCI image metadata
    - Docker Compose metadata
    - image identity
    - provider metadata
    - explicit semantic roles

    No environment-specific application catalog belongs here.
    """

    RULES = (
        (
            AssetRole.CACHE_SERVICE,
            {
                "cache": 5,
                "key value": 5,
                "in memory datastore": 5,
                "in memory database": 4,

                # Generic technology identities.
                "redis": 6,
                "memcached": 6,
            },
        ),
        (
            AssetRole.DATABASE_SERVER,
            {
                "database": 4,
                "database server": 6,
                "relational database": 6,
                "document database": 6,
                "sql database": 6,
                "data store": 3,

                # Generic database technologies.
                "postgres": 6,
                "postgresql": 6,
                "mysql": 6,
                "mariadb": 6,
                "mongodb": 6,
            },
        ),
        (
            AssetRole.SECURITY_NODE,
            {
                "security": 5,
                "firewall": 6,
                "reverse proxy": 6,
                "proxy server": 3,
                "proxy": 2,
                "authentication": 5,
                "authorization": 5,
                "dns server": 4,
                "dns filtering": 6,
                "blocking dns": 6,
                "blocking": 2,
                "vpn": 4,
            },
        ),
        (
            AssetRole.MONITORING_NODE,
            {
                "monitoring": 6,
                "monitor": 4,
                "monitoreo": 6,
                "observability": 6,
                "observabilidad": 6,
                "metrics": 6,
                "metricas": 6,
                "telemetry": 5,
                "telemetria": 5,
                "exporter": 5,
                "alerting": 5,
                "resource usage": 5,
                "performance characteristics": 4,
                "time series metrics": 6,
            },
        ),
        (
            AssetRole.HOME_AUTOMATION,
            {
                "home automation": 7,
                "smart home": 7,
                "domotics": 7,
                "domotica": 7,
                "iot automation": 6,
            },
        ),
        (
            AssetRole.MEDIA_SERVER,
            {
                "media": 5,
                "media server": 7,
                "photo": 4,
                "photos": 4,
                "video": 4,
                "videos": 4,
                "movie": 4,
                "movies": 4,
                "subtitle": 4,
                "subtitles": 4,
                "television": 4,
                "tv show": 4,
                "pvr": 5,
                "torrent": 4,
                "bittorrent": 5,
                "streaming": 5,
                "music library": 5,
            },
        ),
        (
            AssetRole.AI_NODE,
            {
                "machine learning": 5,
                "artificial intelligence": 6,
                "ai inference": 6,
                "model inference": 6,
                "neural network": 5,
            },
        ),
        (
            AssetRole.UTILITY_SERVICE,
            {
                "file management": 5,
                "file browser": 5,
                "synchronization": 5,
                "synchronisation": 5,
                "sync service": 5,
                "sync": 3,
                "container management": 5,
                "administration": 4,
                "automation": 3,
                "update manager": 5,
                "updater": 5,
                "bypass": 6,
                "resolver": 3,
            },
        ),
    )

    OCI_LABELS = (
        "org.opencontainers.image.title",
        "org.opencontainers.image.description",
        "org.opencontainers.image.vendor",
    )

    def classify(
        self,
        name: str,
        metadata: dict | None = None,
    ) -> ApplicationClassification:

        metadata = metadata or {}

        explicit = self._explicit_role(
            metadata
        )

        if explicit is not None:
            return ApplicationClassification(
                role=explicit,
                confidence=1.0,
                reason="explicit application role metadata",
                evidence=(
                    "provider semantic role",
                ),
            )

        fields = self._semantic_fields(
            name,
            metadata,
        )

        scores = {
            role: 0
            for role, _ in self.RULES
        }

        evidence = {
            role: []
            for role, _ in self.RULES
        }

        for source, value in fields:

            normalized = self._normalize(
                value
            )

            if not normalized:
                continue

            for role, terms in self.RULES:

                for term, weight in terms.items():

                    if not self._contains(
                        normalized,
                        term,
                    ):
                        continue

                    scores[role] += weight

                    marker = (
                        f"{source}:{term}"
                    )

                    if marker not in evidence[role]:
                        evidence[role].append(
                            marker
                        )

        role = max(
            scores,
            key=scores.get,
        )

        score = scores[role]

        if score <= 0:
            return ApplicationClassification(
                role=None,
                confidence=0.0,
                reason="insufficient semantic metadata",
            )

        confidence = min(
            0.99,
            0.55 + (
                score * 0.04
            ),
        )

        return ApplicationClassification(
            role=role,
            confidence=confidence,
            reason="semantic runtime metadata classification",
            evidence=tuple(
                evidence[role]
            ),
        )

    def _explicit_role(
        self,
        metadata: dict,
    ) -> AssetRole | None:

        values = []

        for key in (
            "application_role",
            "asset_role",
            "role",
        ):

            value = metadata.get(
                key
            )

            if value:
                values.append(
                    value
                )

        roles = metadata.get(
            "roles"
        )

        if isinstance(
            roles,
            str,
        ):
            values.append(
                roles
            )

        elif isinstance(
            roles,
            (
                list,
                tuple,
                set,
            ),
        ):
            values.extend(
                roles
            )

        for value in values:

            normalized = str(
                value
            ).strip().upper()

            try:
                return AssetRole[
                    normalized
                ]
            except KeyError:
                pass

            try:
                return AssetRole(
                    value
                )
            except (
                ValueError,
                TypeError,
            ):
                pass

        return None

    def _semantic_fields(
        self,
        name: str,
        metadata: dict,
    ) -> list[tuple[str, str]]:

        fields = []

        def add(
            source,
            value,
        ):

            if value is None:
                return

            value = str(
                value
            ).strip()

            if value:
                fields.append(
                    (
                        source,
                        value,
                    )
                )

        # Asset identity itself is valid discovery evidence.
        # Classification still uses only generic concepts.
        add(
            "name",
            name,
        )

        for key in (
            "category",
            "role",
            "compose_service",
            "image",
        ):

            add(
                key,
                metadata.get(
                    key
                ),
            )

        capabilities = metadata.get(
            "capabilities"
        )

        if isinstance(
            capabilities,
            (
                list,
                tuple,
                set,
            ),
        ):

            for capability in capabilities:
                add(
                    "capability",
                    capability,
                )

        labels = (
            metadata.get(
                "labels"
            )
            or {}
        )

        if isinstance(
            labels,
            dict,
        ):

            for key in self.OCI_LABELS:
                add(
                    key,
                    labels.get(
                        key
                    ),
                )

        return fields

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:

        value = unicodedata.normalize(
            "NFKD",
            str(value),
        )

        value = "".join(
            character
            for character in value
            if not unicodedata.combining(
                character
            )
        )

        value = value.lower()

        value = re.sub(
            r"[^a-z0-9]+",
            " ",
            value,
        )

        return " ".join(
            value.split()
        )

    @classmethod
    def _contains(
        cls,
        text: str,
        term: str,
    ) -> bool:

        term = cls._normalize(
            term
        )

        if not term:
            return False

        return (
            f" {term} "
            in f" {text} "
        )

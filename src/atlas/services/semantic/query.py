
from __future__ import annotations

import re
from dataclasses import dataclass, field
import unicodedata
from typing import Any

from atlas.services.semantic.api import AtlasSemanticAPI
from atlas.services.semantic.entity_resolver import (
    SemanticEntityResolver,
)
from atlas.services.semantic.graph_query import (
    SemanticGraphQueryService,
)


@dataclass(slots=True)
class SemanticPlan:
    """
    Canonical semantic interpretation of a natural-language question.

    This object contains intent and structured constraints, but does
    not execute infrastructure operations.
    """

    operation: str

    query: str

    asset_type: str | None = None

    status: str | None = None

    statuses: list[str] = field(
        default_factory=list
    )

    criticality: str | None = None

    role: str | None = None

    target: str | None = None

    direction: str | None = None

    # Exact graph-relation semantics.
    #
    # entity_text is intentionally kept separate from target:
    #
    #   entity_text = language-level reference ("nebula")
    #   target      = resolved semantic reference, when available
    #
    # A target may therefore represent either an ASSET or GROUP.
    entity_text: str | None = None

    relationship: str | None = None

    orientation: str | None = None

    depth: int = 5

    confidence: float = 1.0

    evidence: list[str] = field(
        default_factory=list
    )

    def as_dict(self) -> dict[str, Any]:

        return {
            "operation": self.operation,
            "query": self.query,
            "asset_type": self.asset_type,
            "status": self.status,
            "statuses": list(
                self.statuses
            ),
            "criticality": self.criticality,
            "role": self.role,
            "target": self.target,
            "direction": self.direction,
            "entity_text": self.entity_text,
            "relationship": self.relationship,
            "orientation": self.orientation,
            "depth": self.depth,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
        }


class SemanticQueryEngine:
    """
    Generic semantic query engine for ATLAS.

    IMPORTANT:
    This engine does NOT contain a list of questions.

    It extracts semantic concepts from natural language:

        question
            |
            +--> intent
            +--> asset type
            +--> status
            +--> target asset
            +--> topology direction
            |
            v
        AtlasSemanticAPI

    The LLM remains responsible for natural-language reasoning.
    This layer provides deterministic infrastructure semantics.
    """

    TYPE_KEYWORDS = {
        "VM": (
            "vm",
            "vms",
            "virtual machine",
            "virtual machines",
            "maquina virtual",
            "maquinas virtuales",
        ),
        "LXC": (
            "lxc",
            "lxcs",
            "contenedor lxc",
            "contenedores lxc",
        ),
        "APPLICATION": (
            "application",
            "applications",
            "app",
            "apps",
            "aplicacion",
            "aplicaciones",
        ),
        "CONTAINER": (
            "container",
            "containers",
            "contenedor",
            "contenedores",
        ),
        "DATABASE": (
            "database",
            "databases",
            "db",
            "base de datos",
            "bases de datos",
        ),
        "STORAGE": (
            "storage",
            "disk",
            "disks",
            "disco",
            "discos",
            "almacenamiento",
            "hdd",
            "nvme",
            "ssd",
        ),
        "SERVER": (
            "server",
            "servers",
            "servidor",
            "servidores",
            "host",
            "hosts",
        ),
        "SERVICE": (
            "service",
            "services",
            "servicio",
            "servicios",
            "systemd",
        ),
        "NETWORK": (
            "network",
            "networks",
            "red",
            "redes",
            "networking",
        ),
        "SENSOR": (
            "sensor",
            "sensors",
            "sensores",
        ),
    }

    STATUS_KEYWORDS = {
        "OFFLINE": (
            "offline",
            "down",
            "apagado",
            "apagados",
            "apagada",
            "apagadas",
            "caido",
            "caidos",
            "caida",
            "caidas",
            "fuera de servicio",
            "no funciona",
            "no funcionan",
            "inactivo",
            "inactivos",
        ),
        "ONLINE": (
            "online",
            "up",
            "encendido",
            "encendidos",
            "encendida",
            "encendidas",
            "activo",
            "activos",
            "activa",
            "activas",
            "funcionando",
        ),
        "DEGRADED": (
            "degraded",
            "degradado",
            "degradados",
            "degradada",
            "degradadas",
            "degradacion",
            "degradacion",
            "problemas",
            "problematico",
            "problematicos",
        ),
    }

    ROLE_KEYWORDS = {
        "HYPERVISOR": (
            "hypervisor",
            "hipervisor",
        ),
        "DOCKER_HOST": (
            "docker host",
            "docker-host",
            "host docker",
        ),
        "APPLICATION_SERVER": (
            "application server",
            "servidor de aplicaciones",
        ),
        "DATABASE_SERVER": (
            "database server",
            "servidor de base de datos",
        ),
        "MONITORING_NODE": (
            "monitoring node",
            "nodo de monitoreo",
            "nodo de monitorizacion",
        ),
        "HOME_AUTOMATION": (
            "home automation",
            "automatizacion",
            "home assistant",
        ),
        "STORAGE_NODE": (
            "storage node",
            "nodo de almacenamiento",
        ),
        "MEDIA_SERVER": (
            "media server",
            "servidor multimedia",
        ),
        "SECURITY_NODE": (
            "security node",
            "nodo de seguridad",
            "seguridad",
        ),
        "AI_NODE": (
            "ai node",
            "nodo ai",
            "nodo ia",
            "inteligencia artificial",
        ),
    }

    TOPOLOGY_WORDS = (
        "corre en",
        "corre sobre",
        "ejecuta en",
        "ejecuta sobre",
        "esta en",
        "esta sobre",
        "contiene",
        "contienen",
        "hostea",
        "aloja",
        "alojado",
        "alojados",
        "relacion",
        "relaciones",
        "relacionado",
        "vecinos",
        "neighbor",
        "neighbors",
        "upstream",
        "downstream",
        "hijos",
        "padres",
        "dentro de",
        "sobre que",
    )

    IMPACT_WORDS = (
        "impacto",
        "impact",
        "afecta",
        "afectaria",
        "afectaria",
        "que pasa si",
        "que se cae si",
        "que deja de funcionar si",
        "blast radius",
        "radio de impacto",
        "consecuencia",
        "consecuencias",
    )

    FIND_WORDS = (
        "buscar",
        "busca",
        "encuentra",
        "encontrar",
        "find",
        "search",
        "donde esta",
        "donde se encuentra",
        "cual es",
        "cuales son",
    )

    OVERVIEW_WORDS = (
        "infraestructura",
        "inventario",
        "infrastructure",
        "inventory",
        "panorama",
        "resumen",
        "overview",
        "que tengo",
        "que hay",
        "mostrame todo",
        "muestreme todo",
        "listar todo",
        "lista completa",
    )

    def __init__(
        self,
        api: AtlasSemanticAPI | None = None,
        *,
        entity_resolver=None,
        graph_query=None,
    ):
        self.api = api or AtlasSemanticAPI()

        # Canonical runtime registry.
        # The semantic engine must reason over the live
        # infrastructure model exposed by AtlasSemanticAPI.
        self.registry = self.api.registry

        self.entity_resolver = (
            entity_resolver
            or SemanticEntityResolver(
                self.registry
            )
        )

        self.graph_query = (
            graph_query
            or SemanticGraphQueryService(
                self.registry,
                entity_resolver=(
                    self.entity_resolver
                ),
            )
        )

    # ==============================================================
    # PUBLIC
    # ==============================================================



    def plan(
        self,
        question: str,
    ) -> SemanticPlan:

        if not question or not question.strip():

            return SemanticPlan(
                operation="ERROR",
                query=question or "",
                confidence=0.0,
                evidence=[
                    "empty question"
                ],
            )

        original = question.strip()

        text = self._normalize(
            original
        )

        # ------------------------------------------------------------
        # EXACT GRAPH RELATION
        #
        # Dependency language has graph semantics of its own and must
        # not be collapsed into generic topology direction.
        # ------------------------------------------------------------

        relation = self._parse_relation_query(
            text
        )

        if relation is not None:

            entity_text = relation.get(
                "entity_text"
            )

            entity = (
                self.entity_resolver
                .resolve(
                    entity_text
                )
                if entity_text
                else None
            )

            resolved = bool(
                getattr(
                    entity,
                    "resolved",
                    False,
                )
            )

            return SemanticPlan(
                operation="RELATION",
                query=original,
                target=(
                    entity.reference
                    if resolved
                    else None
                ),
                entity_text=entity_text,
                relationship=relation[
                    "relationship"
                ],
                orientation=relation[
                    "orientation"
                ],
                depth=relation[
                    "depth"
                ],
                confidence=(
                    0.98
                    if resolved
                    else 0.65
                ),
                evidence=[
                    (
                        "exact graph relation "
                        "language detected"
                    ),
                    (
                        "relationship: "
                        + relation[
                            "relationship"
                        ]
                    ),
                    (
                        "orientation: "
                        + relation[
                            "orientation"
                        ]
                    ),
                    (
                        "entity resolved: "
                        + str(
                            entity.reference
                        )
                        if resolved
                        else (
                            "semantic entity missing"
                            if not entity_text
                            else (
                                "semantic entity "
                                "not uniquely resolved"
                            )
                        )
                    ),
                ],
            )

        intent = self._detect_intent(
            text
        )

        asset_type = self._detect_type(
            text
        )

        statuses = self._detect_statuses(
            text
        )

        status = (
            statuses[0]
            if len(statuses) == 1
            else None
        )

        # ------------------------------------------------------------
        # IMPACT
        # ------------------------------------------------------------

        if intent == "IMPACT":

            target = self._resolve_plan_target(
                original
            )

            return SemanticPlan(
                operation="IMPACT",
                query=original,
                target=target,
                depth=5,
                confidence=(
                    0.95
                    if target
                    else 0.70
                ),
                evidence=[
                    "impact language detected",
                    (
                        f"target resolved: {target}"
                        if target
                        else "target not resolved"
                    ),
                ],
            )

        # ------------------------------------------------------------
        # TOPOLOGY
        # ------------------------------------------------------------

        if intent == "TOPOLOGY":

            target = self._resolve_plan_target(
                original
            )

            direction = self._detect_direction(
                text
            )

            return SemanticPlan(
                operation="TOPOLOGY",
                query=original,
                target=target,
                direction=direction,
                depth=5,
                confidence=(
                    0.95
                    if target
                    else 0.70
                ),
                evidence=[
                    "topology language detected",
                    (
                        f"target resolved: {target}"
                        if target
                        else "target not resolved"
                    ),
                ],
            )

        # ------------------------------------------------------------
        # INFRASTRUCTURE OVERVIEW
        # ------------------------------------------------------------

        overview_phrases = (
            "infraestructura",
            "infrastructure",
            "inventario",
            "inventory",
            "todo lo que tengo",
            "todo lo disponible",
            "qué tengo",
            "que tengo",
            "qué hay",
            "que hay",
        )

        is_overview = any(
            phrase in text
            for phrase in overview_phrases
        )

        # A type/status question is inventory, not global overview.
        if is_overview and not (
            asset_type
            or status
            or statuses
        ):

            return SemanticPlan(
                operation="INFRASTRUCTURE",
                query=original,
                confidence=0.95,
                evidence=[
                    "infrastructure overview detected"
                ],
            )

        # ------------------------------------------------------------
        # ASSET INVENTORY
        # ------------------------------------------------------------

        if (
            asset_type
            or status
            or statuses
        ):

            evidence = []

            if asset_type:
                evidence.append(
                    f"asset type detected: {asset_type}"
                )

            if status:
                evidence.append(
                    f"status detected: {status}"
                )

            elif statuses:
                evidence.append(
                    "status selectors detected: "
                    + ", ".join(
                        statuses
                    )
                )

            return SemanticPlan(
                operation="ASSETS",
                query=original,
                asset_type=asset_type,
                status=status,
                statuses=statuses,
                confidence=0.95,
                evidence=evidence,
            )

        # ------------------------------------------------------------
        # FALLBACK
        # ------------------------------------------------------------

        return SemanticPlan(
            operation="FIND",
            query=original,
            confidence=0.50,
            evidence=[
                "no deterministic semantic operation matched"
            ],
        )


    def _resolve_plan_target(
        self,
        question: str,
    ):

        text = self._normalize(
            question
        )

        # ------------------------------------------------------------
        # Extract semantic target from the natural-language question.
        # ------------------------------------------------------------

        patterns = (
            r"qué depende de (.+?)[?]?$",
            r"que depende de (.+?)[?]?$",
            r"qué corre en (.+?)[?]?$",
            r"que corre en (.+?)[?]?$",
            r"qué corre sobre (.+?)[?]?$",
            r"que corre sobre (.+?)[?]?$",
            r"qué pasa si cae (.+?)[?]?$",
            r"que pasa si cae (.+?)[?]?$",
            r"qué se cae si (.+?)[?]?$",
            r"que se cae si (.+?)[?]?$",
            r"impacto de (.+?)[?]?$",
        )

        target_text = None

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
            )

            if match:

                target_text = (
                    match.group(1)
                    .strip()
                    .strip("?")
                    .strip()
                )

                break

        if not target_text:
            return None

        # ------------------------------------------------------------
        # SINGLE SOURCE OF TRUTH
        #
        # SemanticQueryEngine must NOT implement its own asset
        # resolution rules.
        #
        # AssetResolver owns:
        #
        #   exact ID
        #   exact name
        #   semantic duplicate resolution
        #   identity
        #   metadata
        #   partial fallback
        # ------------------------------------------------------------

        resolved = self.api.resolver.resolve(
            target_text
        )

        if resolved is None:
            return None

        return resolved.id


    def query(
        self,
        question: str,
    ) -> dict[str, Any]:

        if not question or not question.strip():
            return {
                "status": "ERROR",
                "error": "question is required",
            }

        original = question.strip()
        text = self._normalize(original)

        semantic = self._extract_semantics(
            original,
            text,
        )

        intent = semantic["intent"]
        target = semantic["target"]

        # ----------------------------------------------------------
        # EXACT GRAPH RELATION
        # ----------------------------------------------------------

        if intent == "RELATION":

            entity_text = semantic.get(
                "entity_text"
            )

            relationship = semantic.get(
                "relationship"
            )

            orientation = semantic.get(
                "orientation"
            )

            if not entity_text:

                return {
                    "status":
                        "NEEDS_TARGET",

                    "intent":
                        intent,

                    "query":
                        original,

                    "message":
                        (
                            "A semantic entity is required "
                            "for relationship analysis."
                        ),
                }

            relation_result = (
                self.graph_query.query(
                    entity_text,
                    relationship=relationship,
                    orientation=orientation,
                    depth=semantic[
                        "depth"
                    ],
                )
            )

            return self._with_metadata(
                relation_result,
                original,
                semantic,
            )

        # ----------------------------------------------------------
        # IMPACT
        # ----------------------------------------------------------

        if intent == "IMPACT":

            if not target:
                return {
                    "status": "NEEDS_TARGET",
                    "intent": intent,
                    "query": original,
                    "message": (
                        "Impact analysis requires a specific "
                        "infrastructure asset."
                    ),
                }

            return self._with_metadata(
                self.api.impact(target),
                original,
                semantic,
            )

        # ----------------------------------------------------------
        # TOPOLOGY
        # ----------------------------------------------------------

        if intent == "TOPOLOGY":

            if target:

                return self._with_metadata(
                    self.api.topology(
                        target,
                        direction=semantic["direction"],
                        depth=semantic["depth"],
                    ),
                    original,
                    semantic,
                )

            # A topology question without a target cannot
            # traverse the graph. Fall back to semantic inventory
            # when a type/role was detected.
            if semantic["asset_type"] or semantic["role"]:

                return self._with_metadata(
                    self.api.assets(
                        asset_type=semantic["asset_type"],
                        role=semantic["role"],
                    ),
                    original,
                    semantic,
                )

            return {
                "status": "NEEDS_TARGET",
                "intent": intent,
                "query": original,
                "message": (
                    "A target asset is required for topology analysis."
                ),
            }

        # ----------------------------------------------------------
        # FIND
        # ----------------------------------------------------------

        if intent == "FIND":

            search_term = semantic["target"]

            if search_term:

                return self._with_metadata(
                    self.api.find(search_term),
                    original,
                    semantic,
                )

            # If no explicit target exists, use the strongest
            # semantic token as a search query.
            token = self._best_search_token(
                text,
                semantic,
            )

            if token:

                return self._with_metadata(
                    self.api.find(token),
                    original,
                    semantic,
                )

        # ----------------------------------------------------------
        # INVENTORY / STATUS / ROLE
        # ----------------------------------------------------------

        if (
            semantic["asset_type"]
            or semantic["status"]
            or semantic.get(
                "statuses"
            )
            or semantic["role"]
        ):

            statuses = list(
                semantic.get(
                    "statuses"
                )
                or []
            )

            if len(statuses) > 1:

                result = (
                    self._assets_for_statuses(
                        statuses,
                        asset_type=(
                            semantic[
                                "asset_type"
                            ]
                        ),
                        role=(
                            semantic[
                                "role"
                            ]
                        ),
                    )
                )

            else:

                result = self.api.assets(
                    status=semantic["status"],
                    asset_type=semantic["asset_type"],
                    role=semantic["role"],
                )

            return self._with_metadata(
                result,
                original,
                semantic,
            )

        # ----------------------------------------------------------
        # SPECIFIC ASSET
        # ----------------------------------------------------------

        if target:

            return self._with_metadata(
                self.api.asset(target),
                original,
                semantic,
            )

        # ----------------------------------------------------------
        # OVERVIEW
        # ----------------------------------------------------------

        if intent == "OVERVIEW":

            return self._with_metadata(
                self.api.infrastructure(),
                original,
                semantic,
            )

        # ----------------------------------------------------------
        # GENERIC FALLBACK
        # ----------------------------------------------------------

        return self._with_metadata(
            self.api.infrastructure(),
            original,
            semantic,
        )

    # ==============================================================
    # SEMANTIC EXTRACTION
    # ==============================================================

    def _extract_semantics(
        self,
        original: str,
        text: str,
    ) -> dict[str, Any]:

        relation = self._parse_relation_query(
            text
        )

        if relation is not None:

            entity_text = relation.get(
                "entity_text"
            )

            entity = (
                self.entity_resolver
                .resolve(
                    entity_text
                )
                if entity_text
                else None
            )

            resolved = bool(
                getattr(
                    entity,
                    "resolved",
                    False,
                )
            )

            return {
                "intent":
                    "RELATION",

                "asset_type":
                    None,

                "status":
                    None,

                "statuses":
                    [],

                "role":
                    None,

                "target":
                    (
                        entity.reference
                        if resolved
                        else None
                    ),

                "direction":
                    None,

                "entity_text":
                    entity_text,

                "relationship":
                    relation[
                        "relationship"
                    ],

                "orientation":
                    relation[
                        "orientation"
                    ],

                "depth":
                    relation[
                        "depth"
                    ],
            }

        asset_type = self._detect_type(text)

        statuses = self._detect_statuses(
            text
        )

        status = (
            statuses[0]
            if len(statuses) == 1
            else None
        )

        role = self._detect_role(text)

        target = self._resolve_plan_target(
            original,
        )

        direction = self._detect_direction(
            text
        )

        depth = self._detect_depth(
            text
        )

        intent = self._detect_intent(
            text,
            asset_type=asset_type,
            status=(
                status
                or (
                    statuses[0]
                    if statuses
                    else None
                )
            ),
            role=role,
            target=target,
        )

        return {
            "intent": intent,
            "asset_type": asset_type,
            "status": status,
            "statuses": statuses,
            "role": role,
            "target": target,
            "direction": direction,
            "entity_text": None,
            "relationship": None,
            "orientation": None,
            "depth": depth,
        }

    # ==============================================================
    # INTENT
    # ==============================================================

    def _detect_intent(
        self,
        text: str,
        *,
        asset_type: str | None = None,
        status: str | None = None,
        role: str | None = None,
        target: str | None = None,
    ) -> str:

        if self._contains_any(
            text,
            self.IMPACT_WORDS,
        ):
            return "IMPACT"

        if self._contains_any(
            text,
            self.TOPOLOGY_WORDS,
        ):
            return "TOPOLOGY"

        if self._contains_any(
            text,
            self.FIND_WORDS,
        ):
            return "FIND"

        if self._contains_any(
            text,
            self.OVERVIEW_WORDS,
        ):
            return "OVERVIEW"

        if (
            asset_type
            or status
            or role
        ):
            return "INVENTORY"

        if target:
            return "ASSET"

        return "OVERVIEW"

    # ==============================================================
    # TYPE
    # ==============================================================

    def _detect_type(
        self,
        text: str,
    ) -> str | None:

        return self._best_category(
            text,
            self.TYPE_KEYWORDS,
        )

    # ==============================================================
    # STATUS
    # ==============================================================

    def _detect_status(
        self,
        text: str,
    ) -> str | None:

        statuses = (
            self._detect_statuses(
                text
            )
        )

        if len(statuses) == 1:
            return statuses[0]

        return None


    def _detect_statuses(
        self,
        text: str,
    ) -> list[str]:

        text = self._normalize(
            text
        )

        detected = []

        ambiguous_online = {
            "activo",
            "activos",
            "activa",
            "activas",
        }

        for (
            category,
            values,
        ) in self.STATUS_KEYWORDS.items():

            matched = False

            for value in values:

                normalized = (
                    self._normalize(
                        value
                    )
                )

                if not normalized:
                    continue

                # "activo(s)" can mean infrastructure assets rather
                # than ONLINE state. Only interpret it as state when
                # used in an explicit state construction such as
                # "servicios estan activos".
                if (
                    category == "ONLINE"
                    and normalized
                    in ambiguous_online
                ):

                    pattern = (
                        r"\b"
                        r"(?:esta|estan|siguen|"
                        r"se encuentran)"
                        r"\s+"
                        + re.escape(
                            normalized
                        )
                        + r"\b"
                    )

                    if re.search(
                        pattern,
                        text,
                    ):
                        matched = True
                        break

                    continue

                pattern = (
                    r"(?<![a-z0-9_])"
                    + re.escape(
                        normalized
                    )
                    + r"(?![a-z0-9_])"
                )

                if re.search(
                    pattern,
                    text,
                ):
                    matched = True
                    break

            if matched:

                detected.append(
                    category
                )

        return detected

    def _assets_for_statuses(
        self,
        statuses,
        *,
        asset_type=None,
        role=None,
    ):

        assets = []
        seen = set()

        for status in statuses:

            result = self.api.assets(
                status=status,
                asset_type=asset_type,
                role=role,
            )

            if (
                not isinstance(
                    result,
                    dict,
                )
                or result.get(
                    "status"
                )
                != "SUCCESS"
            ):

                return result

            for asset in (
                result.get(
                    "assets",
                    []
                )
                or []
            ):

                if not isinstance(
                    asset,
                    dict,
                ):
                    continue

                key = (
                    asset.get(
                        "id"
                    )
                    or repr(
                        asset
                    )
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                assets.append(
                    asset
                )

        return {
            "status":
                "SUCCESS",

            "count":
                len(
                    assets
                ),

            "filters": {
                "status":
                    list(
                        statuses
                    ),

                "asset_type":
                    asset_type,

                "role":
                    role,
            },

            "assets":
                assets,
        }


    # ==============================================================
    # ROLE
    # ==============================================================

    def _detect_role(
        self,
        text: str,
    ) -> str | None:

        return self._best_category(
            text,
            self.ROLE_KEYWORDS,
        )

    # ==============================================================
    # EXACT GRAPH RELATION LANGUAGE
    # ==============================================================

    def _parse_relation_query(
        self,
        text: str,
    ) -> dict[str, Any] | None:
        """
        Translate explicit natural-language relationship grammar into
        graph algebra.

        This parser understands language only.

        It contains no asset names, application names, providers,
        technologies, roles or infrastructure identifiers.

        Graph semantics:

            A DEPENDS_ON B

        means an outgoing edge:

            A --DEPENDS_ON--> B

        Therefore:

            "de que depende A"
                -> OUTGOING

            "que depende de B"
                -> INCOMING
        """

        clean = (
            self._normalize(
                text
            )
            .strip()
            .rstrip("?")
            .strip()
        )

        if not clean:
            return None

        patterns = (

            # ------------------------------------------------------
            # Spanish: dependencies OF entity.
            # ------------------------------------------------------

            (
                r"^de que depende\s+(.+)$",
                "DEPENDS_ON",
                "OUTGOING",
            ),

            (
                r"^cuales son las dependencias de\s+(.+)$",
                "DEPENDS_ON",
                "OUTGOING",
            ),

            (
                r"^dependencias de\s+(.+)$",
                "DEPENDS_ON",
                "OUTGOING",
            ),

            # ------------------------------------------------------
            # Spanish: entities depending ON target.
            # ------------------------------------------------------

            (
                r"^que depende de\s+(.+)$",
                "DEPENDS_ON",
                "INCOMING",
            ),

            (
                r"^que cosas dependen de\s+(.+)$",
                "DEPENDS_ON",
                "INCOMING",
            ),

            # ------------------------------------------------------
            # English equivalents.
            # ------------------------------------------------------

            (
                r"^what does\s+(.+?)\s+depend on$",
                "DEPENDS_ON",
                "OUTGOING",
            ),

            (
                r"^what are the dependencies of\s+(.+)$",
                "DEPENDS_ON",
                "OUTGOING",
            ),

            (
                r"^dependencies of\s+(.+)$",
                "DEPENDS_ON",
                "OUTGOING",
            ),

            (
                r"^what depends on\s+(.+)$",
                "DEPENDS_ON",
                "INCOMING",
            ),
        )

        for (
            pattern,
            relationship,
            orientation,
        ) in patterns:

            match = re.match(
                pattern,
                clean,
            )

            if not match:
                continue

            entity_text = (
                match.group(1)
                .strip()
            )

            if not entity_text:
                return None

            # ------------------------------------------------------
            # INTERROGATIVE PLACEHOLDERS
            #
            # Natural-language placeholders are not infrastructure
            # entities.
            #
            # Examples:
            #
            #   ¿Qué depende de qué?
            #   What depends on what?
            #
            # The relationship itself is understood, but a concrete
            # graph entity is still missing. Preserve RELATION intent
            # and let query() return NEEDS_TARGET.
            # ------------------------------------------------------

            normalized_entity = (
                self._normalize(
                    entity_text
                )
            )

            if normalized_entity in {
                "que",
                "cual",
                "cuales",
                "what",
                "which",
            }:

                entity_text = None

            return {
                "entity_text":
                    entity_text,

                "relationship":
                    relationship,

                "orientation":
                    orientation,

                # Direct relationship questions are one graph edge
                # unless language explicitly requests recursive depth
                # in a future extension.
                "depth":
                    1,
            }

        return None


    # ==============================================================
    # TARGET RESOLUTION
    # ==============================================================

    def _extract_target(
        self,
        original: str,
        *,
        text: str | None = None,
        known_type: str | None = None,
    ) -> str | None:

        normalized = text or self._normalize(
            original
        )

        # ----------------------------------------------------------
        # First: ask the canonical resolver.
        #
        # This is the important part:
        # the semantic layer does not need to know asset names.
        # AssetResolver owns infrastructure identity resolution.
        # ----------------------------------------------------------

        candidates = self._candidate_phrases(
            original,
            normalized,
        )

        for candidate in candidates:

            try:

                resolved = self.resolver.resolve(
                    candidate
                )

                if resolved is not None:

                    if hasattr(
                        resolved,
                        "id",
                    ):
                        return resolved.id

                    if isinstance(
                        resolved,
                        str,
                    ):
                        return resolved

            except Exception:
                pass

        # ----------------------------------------------------------
        # Direct registry matching.
        # ----------------------------------------------------------

        assets = self.registry.assets()

        best = None
        best_score = 0

        for asset in assets:

            names = [
                asset.id,
                asset.name,
            ]

            metadata = getattr(
                asset,
                "metadata",
                {},
            ) or {}

            names.extend(
                str(value)
                for value in metadata.values()
                if value is not None
            )

            for value in names:

                if not value:
                    continue

                candidate = self._normalize(
                    str(value)
                )

                if not candidate:
                    continue

                score = 0

                if candidate in normalized:
                    score += 100

                words = [
                    word
                    for word in candidate.split()
                    if len(word) > 2
                ]

                score += sum(
                    10
                    for word in words
                    if word in normalized
                )

                if known_type:
                    if asset.type.name == known_type:
                        score += 5

                if score > best_score:
                    best_score = score
                    best = asset

        if best is not None and best_score >= 10:
            return best.id

        return None

    # ==============================================================
    # DIRECTION
    # ==============================================================

    def _detect_direction(
        self,
        text: str,
    ) -> str:

        if self._contains_any(
            text,
            (
                "downstream",
                "hijos",
                "dependen de",
                "depende de",
                "que depende",
                "que corre en",
                "que corre sobre",
                "que esta en",
                "que esta sobre",
                "aloja",
                "hostea",
                "contiene",
            ),
        ):
            return "downstream"

        if self._contains_any(
            text,
            (
                "upstream",
                "padres",
                "de que depende",
                "sobre que depende",
                "donde corre",
                "donde esta",
            ),
        ):
            return "upstream"

        if self._contains_any(
            text,
            (
                "critico",
                "critical",
                "criticos",
                "critical upstream",
            ),
        ):
            return "critical_upstream"

        if self._contains_any(
            text,
            (
                "operacional",
                "operational",
            ),
        ):
            return "operational_upstream"

        if self._contains_any(
            text,
            (
                "impacto",
                "blast radius",
                "radio de impacto",
            ),
        ):
            return "blast_radius"

        return "neighbors"

    # ==============================================================
    # DEPTH
    # ==============================================================

    def _detect_depth(
        self,
        text: str,
    ) -> int:

        match = re.search(
            r"\b(?:nivel|niveles|depth|profundidad)\s*(\d+)\b",
            text,
        )

        if not match:
            return 5

        try:
            value = int(
                match.group(1)
            )
        except ValueError:
            return 5

        return max(
            1,
            min(value, 20),
        )

    # ==============================================================
    # SEARCH
    # ==============================================================

    def _best_search_token(
        self,
        text: str,
        semantic: dict[str, Any],
    ) -> str | None:

        ignored = {
            "que",
            "qué",
            "cual",
            "cuales",
            "tengo",
            "hay",
            "esta",
            "están",
            "estan",
            "donde",
            "como",
            "sobre",
            "para",
            "los",
            "las",
            "el",
            "la",
            "un",
            "una",
            "en",
            "de",
            "del",
            "por",
            "con",
            "que",
        }

        tokens = re.findall(
            r"[a-zA-Z0-9._:-]+",
            text,
        )

        semantic_words = set()

        for groups in (
            self.TYPE_KEYWORDS,
            self.STATUS_KEYWORDS,
            self.ROLE_KEYWORDS,
        ):

            for values in groups.values():

                for value in values:

                    semantic_words.update(
                        self._normalize(value).split()
                    )

        candidates = [
            token
            for token in tokens
            if (
                len(token) >= 3
                and token not in ignored
                and token not in semantic_words
            )
        ]

        if not candidates:
            return None

        return max(
            candidates,
            key=len,
        )

    # ==============================================================
    # HELPERS
    # ==============================================================

    def _best_category(
        self,
        text: str,
        categories: dict[str, tuple[str, ...]],
    ) -> str | None:

        best = None
        best_score = 0

        for category, values in categories.items():

            score = 0

            for value in values:

                normalized = self._normalize(
                    value
                )

                if not normalized:
                    continue

                if normalized in text:
                    # Longer semantic expressions are stronger.
                    score += (
                        10
                        + len(normalized.split()) * 3
                    )

            if score > best_score:
                best_score = score
                best = category

        return best

    def _candidate_phrases(
        self,
        original: str,
        normalized: str,
    ) -> list[str]:

        candidates = []

        # Explicit quoted entity.
        candidates.extend(
            re.findall(
                r'"([^"]+)"',
                original,
            )
        )

        candidates.extend(
            re.findall(
                r"'([^']+)'",
                original,
            )
        )

        # Common target constructions.
        patterns = (
            r"\bde\s+(.+)$",
            r"\bsobre\s+(.+)$",
            r"\ben\s+(.+)$",
            r"\ba\s+(.+)$",
        )

        for pattern in patterns:

            match = re.search(
                pattern,
                normalized,
            )

            if match:

                value = match.group(
                    1
                ).strip(
                    " ?.,;:"
                )

                if value:
                    candidates.append(
                        value
                    )

        # Whole question is also useful for AssetResolver.
        candidates.append(
            original
        )

        # Longest candidate first.
        return sorted(
            set(
                item.strip()
                for item in candidates
                if item and item.strip()
            ),
            key=len,
            reverse=True,
        )

    @staticmethod
    def _contains_any(
        text: str,
        values,
    ) -> bool:

        return any(
            value in text
            for value in values
        )

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:

        text = (
            unicodedata.normalize(
                "NFKD",
                text,
            )
            .encode(
                "ascii",
                "ignore",
            )
            .decode(
                "ascii",
            )
            .lower()
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    @staticmethod
    def _with_metadata(
        result: dict[str, Any],
        question: str,
        semantic: dict[str, Any],
    ) -> dict[str, Any]:

        if not isinstance(
            result,
            dict,
        ):
            result = {
                "status": "SUCCESS",
                "result": result,
            }

        result.setdefault(
            "semantic",
            {
                "intent": semantic["intent"],
                "asset_type": semantic["asset_type"],
                "status": semantic["status"],
                "statuses": list(
                    semantic.get(
                        "statuses"
                    )
                    or []
                ),
                "role": semantic["role"],
                "target": semantic["target"],
                "direction": semantic["direction"],
                "entity_text": semantic.get(
                    "entity_text"
                ),
                "relationship": semantic.get(
                    "relationship"
                ),
                "orientation": semantic.get(
                    "orientation"
                ),
                "depth": semantic["depth"],
            },
        )

        result.setdefault(
            "query",
            question,
        )

        return result

from __future__ import annotations

from typing import Any, Callable

from atlas.storage.database import Database
from atlas.storage.incident_repository import (
    IncidentRepository,
)


class OperationalAttentionService:
    """
    Consolidate operational signals that currently require attention.

    This service is technology-neutral.

    Sources:
        - active events
        - unresolved incidents
        - optional current health findings when explicitly provided

    It deliberately does not infer health from product names,
    infrastructure IDs or provider-specific semantics.
    """

    CLOSED_STATUSES = {
        "CLOSED",
        "RESOLVED",
        "CANCELLED",
        "CANCELED",
    }

    CRITICAL_SEVERITIES = {
        "CRITICAL",
        "FATAL",
    }

    SEVERITY_WEIGHT = {
        "CRITICAL": 100,
        "FATAL": 100,
        "ERROR": 90,
        "HIGH": 80,
        "WARNING": 60,
        "WARN": 60,
        "MEDIUM": 50,
        "LOW": 30,
        "INFO": 10,
        "UNKNOWN": 20,
    }


    def __init__(
        self,
        *,
        health_repository=None,
        incident_repository=None,
        active_event_provider: Callable | None = None,
    ) -> None:

        # health_findings currently belongs to a retired collection
        # pipeline. It may still be injected by a future current-state
        # producer, but stale historical findings must not be interpreted
        # as live operational health by default.
        self.health_repository = (
            health_repository
        )

        self.incident_repository = (
            incident_repository
            or IncidentRepository()
        )

        if active_event_provider is None:

            database = Database()

            active_event_provider = (
                database.get_active_events
            )

        self.active_event_provider = (
            active_event_provider
        )


    @staticmethod
    def _value(
        item,
        key,
        default=None,
    ):

        if isinstance(
            item,
            dict,
        ):
            return item.get(
                key,
                default,
            )

        return getattr(
            item,
            key,
            default,
        )


    @classmethod
    def _severity(
        cls,
        value,
    ) -> str:

        normalized = str(
            value
            or "UNKNOWN"
        ).strip().upper()

        if normalized == "WARN":
            return "WARNING"

        return normalized


    @classmethod
    def _status(
        cls,
        value,
    ) -> str:

        return str(
            value
            or "UNKNOWN"
        ).strip().upper()


    @classmethod
    def _item(
        cls,
        *,
        kind,
        item,
    ) -> dict[str, Any]:

        title = (
            cls._value(
                item,
                "title",
            )
            or cls._value(
                item,
                "name",
            )
            or kind.replace(
                "_",
                " ",
            ).title()
        )

        message = (
            cls._value(
                item,
                "message",
            )
            or cls._value(
                item,
                "diagnosis",
            )
            or cls._value(
                item,
                "root_cause",
            )
            or cls._value(
                item,
                "reason",
            )
            or ""
        )

        asset_id = (
            cls._value(
                item,
                "asset_id",
            )
            or cls._value(
                item,
                "asset",
            )
        )

        return {
            "kind":
                kind,

            "id":
                cls._value(
                    item,
                    "id",
                ),

            "asset_id":
                asset_id,

            "severity":
                cls._severity(
                    cls._value(
                        item,
                        "severity",
                    )
                ),

            "status":
                cls._status(
                    cls._value(
                        item,
                        "status",
                    )
                ),

            "title":
                str(title),

            "message":
                str(message),

            "category":
                cls._value(
                    item,
                    "category",
                ),

            "source":
                cls._value(
                    item,
                    "source",
                ),

            "last_seen":
                (
                    cls._value(
                        item,
                        "last_seen",
                    )
                    or cls._value(
                        item,
                        "updated_at",
                    )
                ),
        }


    def summary(
        self,
    ) -> dict[str, Any]:

        items = []
        source_errors = []


        # ---------------------------------------------------------
        # Health findings
        # ---------------------------------------------------------

        findings = []

        if (
            self.health_repository
            is not None
        ):

            try:

                findings = (
                    self.health_repository
                    .get_active()
                )

            except Exception as exc:

                source_errors.append(
                    {
                        "source":
                            "health_findings",

                        "error":
                            str(exc),
                    }
                )


        for finding in findings or []:

            items.append(
                self._item(
                    kind="HEALTH_FINDING",
                    item=finding,
                )
            )


        # ---------------------------------------------------------
        # Active operational events
        # ---------------------------------------------------------

        try:

            events = (
                self.active_event_provider()
            )

        except Exception as exc:

            events = []

            source_errors.append(
                {
                    "source":
                        "active_events",

                    "error":
                        str(exc),
                }
            )


        for event in events or []:

            items.append(
                self._item(
                    kind="EVENT",
                    item=event,
                )
            )


        # ---------------------------------------------------------
        # Unresolved incidents
        # ---------------------------------------------------------

        try:

            get_active_records = getattr(
                self.incident_repository,
                "get_active_records",
                None,
            )

            if callable(
                get_active_records
            ):

                incidents = (
                    get_active_records()
                )

            else:

                incidents = (
                    self.incident_repository
                    .get_all()
                )

        except Exception as exc:

            incidents = []

            source_errors.append(
                {
                    "source":
                        "incidents",

                    "error":
                        str(exc),
                }
            )


        for incident in incidents or []:

            status = self._status(
                self._value(
                    incident,
                    "status",
                )
            )

            if (
                status
                in self.CLOSED_STATUSES
            ):
                continue

            items.append(
                self._item(
                    kind="INCIDENT",
                    item=incident,
                )
            )


        # ---------------------------------------------------------
        # Deduplicate exact operational signals
        # ---------------------------------------------------------

        deduplicated = []
        seen = set()

        for item in items:

            key = (
                item.get(
                    "kind"
                ),
                item.get(
                    "id"
                ),
                item.get(
                    "asset_id"
                ),
                item.get(
                    "title"
                ),
                item.get(
                    "status"
                ),
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            deduplicated.append(
                item
            )


        deduplicated.sort(
            key=lambda item:
                self.SEVERITY_WEIGHT.get(
                    item.get(
                        "severity",
                        "UNKNOWN",
                    ),
                    0,
                ),
            reverse=True,
        )


        attention_required = bool(
            deduplicated
        )


        if any(
            item.get(
                "severity"
            )
            in self.CRITICAL_SEVERITIES
            for item in deduplicated
        ):

            state = "CRITICAL"

        elif attention_required:

            state = "WARNING"

        elif source_errors:

            # Never claim HEALTHY when knowledge sources failed.
            state = "UNKNOWN"

        else:

            state = "HEALTHY"


        by_kind = {}

        by_severity = {}

        for item in deduplicated:

            kind = item.get(
                "kind",
                "UNKNOWN",
            )

            severity = item.get(
                "severity",
                "UNKNOWN",
            )

            by_kind[kind] = (
                by_kind.get(
                    kind,
                    0,
                )
                + 1
            )

            by_severity[severity] = (
                by_severity.get(
                    severity,
                    0,
                )
                + 1
            )


        return {
            "state":
                state,

            "attention_required":
                attention_required,

            "count":
                len(
                    deduplicated
                ),

            "complete":
                not bool(
                    source_errors
                ),

            "summary": {
                "by_kind":
                    by_kind,

                "by_severity":
                    by_severity,
            },

            "items":
                deduplicated,

            "source_errors":
                source_errors,
        }

from __future__ import annotations

from atlas.services.ai.investigator.contracts import (
    InvestigationReport,
)
from atlas.services.ai.investigator.evidence import (
    EvidenceLedger,
)


def render_report(
    report: InvestigationReport,
    ledger: EvidenceLedger,
) -> str:

    if (
        report.status
        == "INSUFFICIENT_EVIDENCE"
    ):

        return (
            "ATLAS no dispone de evidencia "
            "verificada suficiente para responder."
        )

    facts = ledger.selected(
        report.fact_ids
    )

    if not facts:

        return (
            "ATLAS no dispone de evidencia "
            "verificada suficiente para responder."
        )

    # --------------------------------------------------------------
    # ATTENTION
    # --------------------------------------------------------------

    attention = [
        fact
        for fact in facts
        if fact.kind == "ATTENTION"
    ]

    if (
        attention
        and len(attention) == len(facts)
    ):

        count = len(
            attention
        )

        if count == 1:

            lines = [
                (
                    "ATLAS registra 1 señal verificada "
                    "que requiere atención:"
                )
            ]

        else:

            lines = [
                (
                    f"ATLAS registra {count} señales verificadas "
                    "que requieren atención:"
                )
            ]

        for fact in attention:

            line = (
                f"- **{fact.severity}** — "
                f"{fact.title}"
            )

            if fact.signal_id:

                line += (
                    f" · {fact.signal_id}"
                )

            if fact.asset_id:

                line += (
                    f" · {fact.asset_id}"
                )

            if fact.message:

                line += (
                    f": {fact.message}"
                )

            lines.append(
                line
            )

        return "\n".join(
            lines
        )

    # --------------------------------------------------------------
    # STATUS
    # --------------------------------------------------------------

    status_queries = [
        fact
        for fact in facts
        if fact.kind == "STATUS_QUERY"
    ]

    status_assets = [
        fact
        for fact in facts
        if fact.kind == "STATUS"
    ]

    if (
        status_queries
        and (
            len(
                status_queries
            )
            + len(
                status_assets
            )
            == len(
                facts
            )
        )
    ):

        if len(
            status_queries
        ) != 1:

            return (
                "ATLAS obtuvo evidencia verificada de estado, "
                "pero el renderer requiere una única consulta "
                "de estado por respuesta."
            )

        query = status_queries[
            0
        ]

        if not query.complete:

            return (
                "ATLAS no dispone de evidencia "
                "verificada suficiente para responder."
            )

        filters = []

        if query.status_filter:

            filters.append(
                f"status={query.status_filter}"
            )

        if query.asset_type:

            filters.append(
                f"asset_type={query.asset_type}"
            )

        if query.criticality:

            filters.append(
                f"criticality={query.criticality}"
            )

        if query.role:

            filters.append(
                f"role={query.role}"
            )

        filter_text = (
            ", ".join(
                filters
            )
            if filters
            else "sin filtros adicionales"
        )

        if query.count == 0:

            return (
                "ATLAS verificó una consulta completa "
                "sobre el inventario actual y no encontró "
                "assets que coincidan con "
                f"{filter_text}."
            )

        linked_assets = [
            fact
            for fact in status_assets
            if fact.query_fact_id
            == query.id
        ]

        if not linked_assets:

            return (
                "ATLAS verificó "
                f"{query.count} assets que coinciden con "
                f"{filter_text}."
            )

        lines = [
            (
                "Según evidencia verificada de ATLAS, "
                f"{query.count} assets coinciden con "
                f"{filter_text}:"
            )
        ]

        for fact in linked_assets:

            name = (
                fact.asset_name
                or fact.asset_id
            )

            line = (
                f"- `{name}` — "
                f"{fact.status}"
            )

            if fact.asset_type:

                line += (
                    f" · {fact.asset_type}"
                )

            if fact.health is not None:

                line += (
                    f" · health={fact.health:g}"
                )

            lines.append(
                line
            )

        return "\n".join(
            lines
        )

    # --------------------------------------------------------------
    # RELATIONS
    # --------------------------------------------------------------

    relations = [
        fact
        for fact in facts
        if fact.kind == "RELATION"
    ]

    if (
        relations
        and len(relations) == len(facts)
    ):

        predicates = {
            fact.predicate
            for fact in relations
        }

        subject_ids = {
            fact.subject_id
            for fact in relations
        }

        if (
            predicates
            == {
                "DEPENDS_ON"
            }
            and len(subject_ids) == 1
        ):

            subject_id = next(
                iter(
                    subject_ids
                )
            )

            subject_fact = next(
                fact
                for fact in relations
                if fact.subject_id
                == subject_id
            )

            subject = (
                subject_fact.subject_name
                or subject_id
            )

            count = len(
                relations
            )

            if count == 1:

                description = (
                    "1 dependencia directa registrada"
                )

            else:

                description = (
                    f"{count} dependencias directas registradas"
                )

            lines = [
                (
                    "Según evidencia verificada de ATLAS, "
                    f"`{subject}` tiene {description}:"
                )
            ]

            for fact in relations:

                target = (
                    fact.object_name
                    or fact.object_id
                )

                lines.append(
                    f"- `{target}`"
                )

            return "\n".join(
                lines
            )

        lines = [
            "Relaciones verificadas por ATLAS:"
        ]

        for fact in relations:

            subject = (
                fact.subject_name
                or fact.subject_id
            )

            target = (
                fact.object_name
                or fact.object_id
            )

            lines.append(
                (
                    f"- `{subject}` "
                    f"{fact.predicate} "
                    f"`{target}`"
                )
            )

        return "\n".join(
            lines
        )

    return (
        "ATLAS obtuvo evidencia verificada, "
        "pero el renderer todavía no soporta "
        "esa combinación de hechos."
    )

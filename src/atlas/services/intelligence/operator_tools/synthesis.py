"""
Deterministic synthesis for verified Intelligence tool results.

Tool-specific result schemas belong here, next to the Intelligence
tool layer.

AIService only asks whether a tool can be synthesized and delegates
the actual interpretation.
"""

from collections.abc import Callable


Synthesizer = Callable[
    [str, object],
    str | None,
]


def _smart(
    user_prompt: str,
    data: object,
) -> str | None:
    """
    Synthesize SMART telemetry for one or more physical disks.

    Telemetry providers may return either a single record or a list
    of records. The synthesis layer owns that result-shape knowledge;
    AIService remains completely generic.
    """

    if isinstance(
        data,
        dict,
    ):
        records = [
            data,
        ]

    elif isinstance(
        data,
        list,
    ):
        records = [
            item
            for item in data
            if isinstance(
                item,
                dict,
            )
        ]

    else:
        return None

    if not records:
        return None

    # Put useful SMART records first while preserving discovery order
    # among equivalent entries.
    records = sorted(
        records,
        key=lambda item: (
            item.get(
                "temperature_c"
            ) is None,
            not bool(
                item.get(
                    "smart_available"
                )
            ),
        ),
    )

    lines = []

    for record in records:

        device = record.get(
            "device"
        )

        model = record.get(
            "model"
        )

        temperature = record.get(
            "temperature_c"
        )

        health = record.get(
            "health"
        )

        smart_available = record.get(
            "smart_available"
        )

        error = record.get(
            "error"
        )

        identity = []

        if model:
            identity.append(
                str(model)
            )

        if device:
            identity.append(
                f"({device})"
            )

        target = (
            " ".join(
                identity
            )
            if identity
            else "Disco"
        )

        values = []

        if temperature is not None:

            values.append(
                "temperatura "
                f"**{float(temperature):.2f} °C**"
            )

        if health:

            values.append(
                f"SMART **{health}**"
            )

        if (
            not values
            and smart_available is False
        ):

            values.append(
                "SMART no disponible"
            )

        if (
            not values
            and error
        ):

            values.append(
                f"sin telemetría SMART ({error})"
            )

        if not values:
            continue

        lines.append(
            f"{target}: "
            + " · ".join(
                values
            )
            + "."
        )

    if not lines:
        return None

    return "\n".join(
        lines
    )


def _cpu_temperature(
    user_prompt: str,
    data: dict,
) -> str | None:

    temperature = data.get(
        "temperature_c"
    )

    if temperature is None:
        return None

    return (
        "La temperatura actual del CPU es "
        f"**{float(temperature):.2f} °C**."
    )


def _proxmox_storage(
    user_prompt: str,
    data: dict,
) -> str | None:

    thin_pool = (
        data.get(
            "thin_pool"
        )
        or {}
    )

    lvm = (
        data.get(
            "lvm"
        )
        or {}
    )

    physical_disks = (
        data.get(
            "physical_disks"
        )
        or []
    )

    free_gb = (
        thin_pool.get(
            "free_gb"
        )
    )

    if free_gb is None:

        free_gb = lvm.get(
            "free_gb"
        )

    parts = []

    if free_gb is not None:

        parts.append(
            "espacio libre "
            f"**{float(free_gb):.2f} GB**"
        )

    disks = []

    for disk in physical_disks:

        if not isinstance(
            disk,
            dict,
        ):
            continue

        values = []

        device = disk.get(
            "device"
        )

        model = disk.get(
            "model"
        )

        size_gb = disk.get(
            "size_gb"
        )

        if device:
            values.append(
                str(device)
            )

        if model:
            values.append(
                str(model)
            )

        if size_gb is not None:

            values.append(
                f"{float(size_gb):.2f} GB"
            )

        if values:

            disks.append(
                " — ".join(
                    values
                )
            )

    if disks:

        parts.append(
            "discos: "
            + "; ".join(
                disks
            )
        )

    if not parts:
        return None

    return (
        "Almacenamiento Proxmox: "
        + " · ".join(
            parts
        )
        + "."
    )


def _attention(
    user_prompt: str,
    data: object,
) -> str | None:

    if not isinstance(
        data,
        dict,
    ):
        return None

    attention = (
        data.get("attention")
        or {}
    )

    if not isinstance(
        attention,
        dict,
    ):
        return None

    state = str(
        attention.get("state")
        or "UNKNOWN"
    ).upper()

    complete = bool(
        attention.get(
            "complete",
            False,
        )
    )

    required = bool(
        attention.get(
            "attention_required",
            False,
        )
    )

    items = [
        item
        for item in (
            attention.get("items")
            or []
        )
        if isinstance(item, dict)
    ]


    if (
        complete
        and not required
    ):

        return (
            "ATLAS no detecta señales operativas actuales "
            "que requieran atención."
        )


    if (
        not complete
        and not items
    ):

        return (
            "ATLAS no pudo verificar completamente el "
            "estado operativo actual."
        )


    count = len(items)

    lines = [
        (
            f"Estado operativo **{state}**. "
            f"ATLAS detecta **{count} "
            + (
                "señal"
                if count == 1
                else "señales"
            )
            + "** que requieren atención."
        )
    ]


    for item in items:

        severity = str(
            item.get("severity")
            or "UNKNOWN"
        ).upper()

        title = str(
            item.get("title")
            or item.get("kind")
            or "Operational signal"
        )

        identifier = item.get("id")
        asset_id = item.get("asset_id")

        message = str(
            item.get("message")
            or ""
        ).strip()

        identity = []

        if identifier is not None:
            identity.append(
                str(identifier)
            )

        if asset_id:
            identity.append(
                str(asset_id)
            )

        suffix = (
            " · " + " · ".join(identity)
            if identity
            else ""
        )

        line = (
            f"- **{severity}** — "
            f"{title}{suffix}"
        )

        if message:
            line += f": {message}"

        lines.append(line)


    if not complete:

        lines.append(
            "La evaluación es parcial porque una o más "
            "fuentes de conocimiento no estuvieron disponibles."
        )


    return "\n".join(lines)


# ---------------------------------------------------------------------
# Tool-specific knowledge lives HERE, not in AIService.
# ---------------------------------------------------------------------

_TOOL_SYNTHESIZERS: dict[
    str,
    Synthesizer,
] = {

    "atlas_get_attention":
        _attention,

    "telemetry_smart":
        _smart,

    "telemetry_proxmox_cpu_temperature":
        _cpu_temperature,

    "telemetry_proxmox_storage":
        _proxmox_storage,

}


def can_synthesize_tool(
    tool_name: str,
) -> bool:

    return (
        tool_name
        in _TOOL_SYNTHESIZERS
    )


def synthesize_verified_tool_results(
    user_prompt: str,
    results: list[dict],
) -> str | None:
    """
    Synthesize one or more verified tool results.

    Unsupported tools simply return None so the normal LLM
    synthesis path can continue.
    """

    answers = []

    for item in results:

        if not isinstance(
            item,
            dict,
        ):
            continue

        tool_name = item.get(
            "name"
        )

        raw_result = (
            item.get(
                "result"
            )
            or {}
        )

        if not isinstance(
            raw_result,
            dict,
        ):
            continue

        if not raw_result.get(
            "success",
            False,
        ):
            continue

        data = raw_result.get(
            "data"
        )

        if data is None:
            continue

        synthesizer = (
            _TOOL_SYNTHESIZERS.get(
                tool_name
            )
        )

        if synthesizer is None:
            continue

        answer = synthesizer(
            user_prompt,
            data,
        )

        if answer:
            answers.append(
                answer
            )

    if not answers:
        return None

    return "\n".join(
        answers
    )

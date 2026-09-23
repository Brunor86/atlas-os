def completed_status(
    metadata,
) -> str:

    metadata = (
        metadata
        if isinstance(
            metadata,
            dict,
        )
        else {}
    )

    status = str(
        metadata.get(
            "agent_status",
            ""
        )
        or ""
    ).strip().upper()

    if status:
        return status

    # Compatibility fallback for callers that do not yet
    # provide agent_status metadata.
    return "SUCCESS"

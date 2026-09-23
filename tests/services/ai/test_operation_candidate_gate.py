from atlas.services.ai.service import (
    _is_operation_candidate,
)


def test_operation_candidate_gate():

    assert _is_operation_candidate(
        "Reiniciá atlas-collector.service"
    )

    assert _is_operation_candidate(
        "Detené atlas-web.service"
    )

    assert _is_operation_candidate(
        "Arrancá flaresolverr"
    )

    assert _is_operation_candidate(
        "Restart docker.service"
    )


    assert not _is_operation_candidate(
        "¿Está funcionando atlas-collector.service?"
    )

    assert not _is_operation_candidate(
        "Atlas collector está fallando, ¿qué hago?"
    )

    assert not _is_operation_candidate(
        "¿Qué pasa si detengo flaresolverr?"
    )

    assert not _is_operation_candidate(
        "Mostrame los servicios de Atlas"
    )

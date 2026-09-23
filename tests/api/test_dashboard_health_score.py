from pathlib import Path

from atlas.api.dashboard import (
    health_score_from_noc_score,
)


def test_dashboard_health_score_contract():

    cases = {
        0: 100,
        1: 99,
        20: 80,
        29: 71,
        30: 70,
        69: 31,
        70: 30,
        100: 0,
        140: 0,
        -10: 100,
    }

    for noc_score, expected in cases.items():

        assert (
            health_score_from_noc_score(
                noc_score
            )
            == expected
        )


    template = Path(
        "src/atlas/api/templates/index.html"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "{{ noc.summary.health_score }}"
        in template
    )

    assert (
        "{{ noc.summary.score }}"
        not in template
    )

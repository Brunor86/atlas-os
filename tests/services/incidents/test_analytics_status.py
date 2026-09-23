from atlas.services.incidents.analytics import (
    IncidentAnalytics,
)


class FakeRepository:

    def get_all(
        self,
    ):

        return [
            (
                "INC-0001",
                "one",
                "asset-1",
                "CRITICAL",
                "OPEN",
            ),
            (
                "INC-0002",
                "two",
                "asset-2",
                "MEDIUM",
                "RECOVERING",
            ),
            (
                "INC-0003",
                "three",
                "asset-3",
                "MEDIUM",
                "RESOLVED",
            ),
        ]


    def get_active_records(
        self,
    ):

        return [
            {
                "id":
                    "INC-0001",

                "severity":
                    "CRITICAL",

                "status":
                    "OPEN",
            },
            {
                "id":
                    "INC-0002",

                "severity":
                    "MEDIUM",

                "status":
                    "RECOVERING",
            },
        ]


    def count_by_title(
        self,
    ):

        return [
            (
                "one",
                1,
            ),
            (
                "two",
                1,
            ),
            (
                "three",
                1,
            ),
        ]


def test_summary_counts_only_active_as_open():

    analytics = IncidentAnalytics(
        repository=FakeRepository()
    )

    result = analytics.summary()

    assert result["total"] == 3
    assert result["open"] == 2
    assert result["critical"] == 1


def test_severity_distribution_excludes_resolved():

    analytics = IncidentAnalytics(
        repository=FakeRepository()
    )

    assert (
        analytics.severity_distribution()
        == {
            "CRITICAL": 1,
            "WARNING": 0,
            "MEDIUM": 1,
            "LOW": 0,
        }
    )

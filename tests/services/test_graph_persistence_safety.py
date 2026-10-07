from types import SimpleNamespace

from atlas.services.assets.graph_service import AssetGraphService


class RecordingRepository:

    def __init__(self):
        self.cleared = 0
        self.saved = []

    def clear_relationships(self):
        self.cleared += 1

    def save_relationship(self, relationship):
        self.saved.append(relationship)


def service_with_repository():
    service = AssetGraphService()
    service.repository = RecordingRepository()
    return service


def test_partial_discovery_preserves_last_known_good_graph():
    service = service_with_repository()
    relationship = SimpleNamespace(source="a", target="b")

    result = service.persist(
        [relationship],
        authoritative=False,
    )

    assert result is False
    assert service.repository.cleared == 0
    assert service.repository.saved == []


def test_authoritative_discovery_replaces_graph():
    service = service_with_repository()
    relationships = [
        SimpleNamespace(source="a", target="b"),
        SimpleNamespace(source="b", target="c"),
    ]

    result = service.persist(
        relationships,
        authoritative=True,
    )

    assert result is True
    assert service.repository.cleared == 1
    assert service.repository.saved == relationships

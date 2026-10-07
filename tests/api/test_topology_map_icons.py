from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def test_map_links_service_iconography_assets():
    template = (
        ROOT
        / "src/atlas/api/templates/partials/topology_map.html"
    ).read_text()

    assert (
        "atlas-map-icons.css"
        in template
    )

    assert (
        "atlas-map-icons.js"
        in template
    )


def test_service_icon_registry_covers_core_atlas_services():
    javascript = (
        ROOT
        / "src/atlas/api/static/js/atlas-map-icons.js"
    ).read_text()

    expected = (
        "proxmox",
        "homeassistant",
        "tailscale",
        "docker",
        "grafana",
        "prometheus",
        "immich",
        "postgresql",
        "olivasat",
        "atlas-ai",
        "zigbee",
        "sonoff",
    )

    lowered = (
        javascript.lower()
    )

    for value in expected:
        assert value in lowered

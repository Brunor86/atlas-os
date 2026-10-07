from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

INDEX = ROOT / "src/atlas/api/templates/index.html"
HTML = ROOT / "src/atlas/api/templates/partials/topology_map.html"
JS = ROOT / "src/atlas/api/static/js/atlas.js"
CSS = ROOT / "src/atlas/api/static/css/atlas.css"


def normalized(path):
    return " ".join(path.read_text(encoding="utf-8").split())


def map_section():
    js = normalized(JS)
    start = js.index("ATLAS MAP v1")
    end = js.index("form.addEventListener", start)
    return js[start:end]


def test_map_is_mounted_in_dashboard():
    index = normalized(INDEX)
    html = normalized(HTML)
    assert "partials/topology_map.html" in index
    assert "id=\"atlasTopologyMap\"" in html
    assert "id=\"atlasMapCanvas\"" in html
    assert "id=\"atlasMapDetail\"" in html


def test_map_frontend_is_read_only():
    section = map_section()
    assert "/api/topology/map" in section
    for value in (
        "method: \"POST\"",
        "method: \"PUT\"",
        "method: \"PATCH\"",
        "method: \"DELETE\"",
        "/approve",
        "/reject",
        "/reverify",
    ):
        assert value not in section


def test_map_has_interactive_controls():
    html = normalized(HTML)
    section = map_section()
    for value in (
        "atlasMapSearch",
        "atlasMapServices",
        "atlasMapRefresh",
    ):
        assert value in html
        assert value in section


def test_services_are_hidden_by_default():
    section = map_section()
    assert "node.type === \"SERVICE\"" in section
    assert "&& !showServices" in section


def test_map_has_graph_engine():
    section = map_section()
    for value in (
        "function atlasMapDepths",
        "function atlasMapRender",
        "function atlasMapShowDetail",
        "atlas-map-edge",
        "atlas-map-node",
    ):
        assert value in section


def test_map_has_visual_contract():
    css = normalized(CSS)
    for value in (
        ".atlas-map-layout",
        ".atlas-map-canvas",
        ".atlas-map-edge",
        ".atlas-map-node",
        ".atlas-map-node.online",
        ".atlas-map-node.offline",
        ".atlas-map-node.degraded",
        ".atlas-map-detail",
    ):
        assert value in css
    assert "@media (max-width: 900px)" in css


def test_map_does_not_hardcode_real_assets():
    section = map_section()
    for value in (
        "debian-docker",
        "atlas-windows",
        "DB-Aceite",
        "olivasat",
        "immich_server",
    ):
        assert value not in section

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

BASE = (
    ROOT
    / "src/atlas/api/templates/base.html"
)

SERVER = (
    ROOT
    / "src/atlas/api/server.py"
)


def test_static_assets_use_content_versioned_urls():

    base = BASE.read_text()

    assert (
        "css/atlas.css"
        in base
    )

    assert (
        "js/atlas.js"
        in base
    )

    assert (
        "?v={{ static_asset_version }}"
        in base
    )

    assert (
        base.count(
            "?v={{ static_asset_version }}"
        )
        == 2
    )


def test_static_version_is_derived_from_asset_content():

    server = SERVER.read_text()

    assert (
        "hashlib.sha256()"
        in server
    )

    assert (
        "BASE_DIR / \"static/css/atlas.css\""
        in server
    )

    assert (
        "BASE_DIR / \"static/js/atlas.js\""
        in server
    )

    assert (
        "STATIC_ASSET_VERSION"
        in server
    )

    assert (
        "\"static_asset_version\":"
        in server
    )

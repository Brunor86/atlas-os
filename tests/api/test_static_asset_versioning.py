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

    version_suffix = (
        "?v={{ static_asset_version }}"
    )

    expected_assets = (
        "css/atlas.css",
        "css/atlas-sky.css",
        "js/atlas.js",
    )

    for asset in expected_assets:
        assert asset in base

    assert (
        base.count(
            version_suffix
        )
        == len(expected_assets)
    )


def test_static_version_is_derived_from_asset_content():

    server = SERVER.read_text()

    assert (
        "hashlib.sha256()"
        in server
    )

    expected_hashed_assets = (
        'BASE_DIR / "static/css/atlas.css"',
        'BASE_DIR / "static/css/atlas-sky.css"',
        'BASE_DIR / "static/js/atlas.js"',
    )

    for asset in expected_hashed_assets:
        assert asset in server

    assert (
        "STATIC_ASSET_VERSION"
        in server
    )

    assert (
        '"static_asset_version":'
        in server
    )

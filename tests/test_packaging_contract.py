import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _pyproject():
    return tomllib.loads(
        (
            ROOT
            / "pyproject.toml"
        ).read_text(
            encoding="utf-8",
        )
    )


def _dependency_name(
    value: str,
) -> str:

    name = re.split(
        r"[<>=!~\[]",
        value,
        maxsplit=1,
    )[0]

    return (
        name.strip()
        .lower()
        .replace("_", "-")
    )


def test_runtime_dependencies_are_declared():

    project = _pyproject()[
        "project"
    ]

    declared = {
        _dependency_name(
            dependency
        )
        for dependency
        in project[
            "dependencies"
        ]
    }

    required = {
        "typer",
        "rich",
        "psutil",
        "pydantic",
        "pydantic-ai",
        "mcp",
        "docker",
        "fastapi",
        "requests",
        "jinja2",
        "uvicorn",
    }

    assert required <= declared


def test_dashboard_resources_are_packaged():

    config = _pyproject()

    package_data = (
        config[
            "tool"
        ][
            "setuptools"
        ][
            "package-data"
        ][
            "atlas.api"
        ]
    )

    assert (
        "templates/*.html"
        in package_data
    )

    assert (
        "templates/partials/*.html"
        in package_data
    )

    assert (
        "static/css/*.css"
        in package_data
    )

    assert (
        "static/js/*.js"
        in package_data
    )


def test_requirements_delegates_to_pyproject():

    lines = [
        line.strip()
        for line in (
            ROOT
            / "requirements.txt"
        ).read_text(
            encoding="utf-8",
        ).splitlines()
        if line.strip()
        and not line.lstrip().startswith(
            "#"
        )
    ]

    assert lines == [
        "."
    ]

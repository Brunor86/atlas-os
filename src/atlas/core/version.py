import re
import subprocess

from importlib import metadata
from pathlib import Path


PACKAGE_NAME = "atlasctl"

# Source-tree layout:
#
#   <repository>/src/atlas/core/version.py
#
# Installed wheels do not have this layout and therefore must
# resolve their version from distribution metadata instead.
SOURCE_REPOSITORY = (
    Path(__file__)
    .resolve()
    .parents[3]
)


def _package_display_version(
    version: str,
) -> str:
    """
    Convert a PEP 440 package version to the public
    ATLAS release-label format.

    Examples:

        1.0.0       -> v1.0.0
        1.0.0rc1    -> v1.0.0-rc1
    """

    value = str(
        version
        or ""
    ).strip()

    if not value:
        return "development"

    if value.startswith(
        "v"
    ):
        return value

    rc = re.fullmatch(
        r"(\d+\.\d+\.\d+)rc(\d+)",
        value,
    )

    if rc:
        return (
            f"v{rc.group(1)}"
            f"-rc{rc.group(2)}"
        )

    return (
        "v"
        + value
    )


def _git_version() -> str | None:
    """
    Resolve a release tag only from the ATLAS source checkout.

    Never inspect the caller's current working directory. This
    prevents an installed wheel from accidentally reporting a
    version belonging to an unrelated Git repository.
    """

    repository = (
        SOURCE_REPOSITORY
    )

    if not (
        repository
        / ".git"
    ).exists():

        return None

    try:

        value = subprocess.check_output(
            [
                "git",
                "describe",
                "--tags",
                "--abbrev=0",
            ],
            cwd=repository,
            stderr=subprocess.DEVNULL,
        ).decode().strip()

    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        OSError,
    ):

        return None

    return (
        value
        or None
    )


def _installed_package_version() -> str | None:

    try:

        return metadata.version(
            PACKAGE_NAME
        )

    except metadata.PackageNotFoundError:

        return None


def get_version() -> str:
    """
    Resolve the ATLAS runtime version.

    A source checkout prefers its own Git release tag.

    An installed wheel does not require Git and uses its
    canonical PEP 440 package metadata.

    A raw source tree without Git metadata and without an
    installed distribution is reported as development.
    """

    git_version = (
        _git_version()
    )

    if git_version:
        return git_version

    package_version = (
        _installed_package_version()
    )

    if package_version:
        return _package_display_version(
            package_version
        )

    return "development"


__version__ = get_version()

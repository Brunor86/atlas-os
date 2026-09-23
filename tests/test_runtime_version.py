import subprocess

from importlib import metadata
from pathlib import Path

from typer.testing import CliRunner

import atlas.core.version as version

from atlas.cli import app


def test_package_display_version_contract():

    assert (
        version._package_display_version(
            "1.0.0"
        )
        == "v1.0.0"
    )

    assert (
        version._package_display_version(
            "1.0.0rc1"
        )
        == "v1.0.0-rc1"
    )

    assert (
        version._package_display_version(
            "2.4.1"
        )
        == "v2.4.1"
    )


def test_git_version_is_scoped_to_atlas_repository(
    monkeypatch,
    tmp_path,
):

    repository = (
        tmp_path
        / "atlas-source"
    )

    repository.mkdir()

    (
        repository
        / ".git"
    ).write_text(
        "gitdir: synthetic\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        version,
        "SOURCE_REPOSITORY",
        repository,
    )

    observed = {}

    def fake_check_output(
        command,
        **kwargs,
    ):

        observed[
            "command"
        ] = command

        observed[
            "cwd"
        ] = kwargs.get(
            "cwd"
        )

        return (
            b"v2.3.4-rc2\n"
        )

    monkeypatch.setattr(
        subprocess,
        "check_output",
        fake_check_output,
    )

    assert (
        version._git_version()
        == "v2.3.4-rc2"
    )

    assert (
        observed[
            "cwd"
        ]
        == repository
    )


def test_git_is_not_called_without_source_repository(
    monkeypatch,
    tmp_path,
):

    repository = (
        tmp_path
        / "installed-layout"
    )

    repository.mkdir()

    monkeypatch.setattr(
        version,
        "SOURCE_REPOSITORY",
        repository,
    )

    def unexpected_git(
        *args,
        **kwargs,
    ):

        raise AssertionError(
            "Git must not be invoked "
            "for an installed wheel"
        )

    monkeypatch.setattr(
        subprocess,
        "check_output",
        unexpected_git,
    )

    assert (
        version._git_version()
        is None
    )


def test_source_checkout_prefers_git_tag(
    monkeypatch,
):

    monkeypatch.setattr(
        version,
        "_git_version",
        lambda:
            "v2.3.4-rc2",
    )

    monkeypatch.setattr(
        version,
        "_installed_package_version",
        lambda:
            "9.9.9",
    )

    assert (
        version.get_version()
        == "v2.3.4-rc2"
    )


def test_wheel_uses_distribution_metadata_without_git(
    monkeypatch,
):

    monkeypatch.setattr(
        version,
        "_git_version",
        lambda:
            None,
    )

    monkeypatch.setattr(
        metadata,
        "version",
        lambda name:
            "1.0.0rc1",
    )

    assert (
        version.get_version()
        == "v1.0.0-rc1"
    )


def test_raw_source_without_git_or_distribution_is_development(
    monkeypatch,
):

    monkeypatch.setattr(
        version,
        "_git_version",
        lambda:
            None,
    )

    def no_distribution(
        name,
    ):

        raise metadata.PackageNotFoundError(
            name
        )

    monkeypatch.setattr(
        metadata,
        "version",
        no_distribution,
    )

    assert (
        version.get_version()
        == "development"
    )


def test_cli_version_uses_runtime_version():

    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "version",
        ],
    )

    assert result.exit_code == 0

    assert (
        version.__version__
        in result.stdout
    )

    assert (
        "106.0"
        not in result.stdout
    )

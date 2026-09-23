from pathlib import Path
import subprocess


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


BUILDER = (
    ROOT
    / "scripts"
    / "build-release-bundle.sh"
)


def source():

    return BUILDER.read_text(
        encoding="utf-8"
    )


def test_release_bundle_builder_exists():

    assert BUILDER.is_file()


def test_release_bundle_builder_shell_syntax():

    subprocess.run(
        [
            "bash",
            "-n",
            str(
                BUILDER
            ),
        ],
        check=True,
    )


def test_release_bundle_requires_clean_worktree():

    text = source()

    assert (
        "git -C"
        in text
    )

    assert (
        "status --porcelain"
        in text
    )

    assert (
        "release bundle requires a clean Git worktree"
        in text
    )


def test_release_bundle_builds_wheel_without_git_runtime():

    text = source()

    assert (
        "-m pip"
        in text
    )

    assert (
        "wheel"
        in text
    )

    assert (
        "--no-deps"
        in text
    )

    assert (
        "Runtime-Git-Required: no"
        in text
    )

    assert (
        "Prometheus: optional"
        in text
    )

    assert (
        "License: Apache-2.0"
        in text
    )


def test_release_bundle_contains_install_assets():

    text = source()

    required = (
        "scripts/install-atlas.sh",
        "ops/bin/atlas-wait-ready",
        "ops/config/atlas.env.example",
        "ops/config/atlas-web.env.example",
        "ops/systemd/atlas-collector.service",
        "ops/systemd/atlas-web.service",
        "boot-hardening.conf",
        "docs/INSTALL_V1.md",
        "LICENSE",
    )

    for value in required:

        assert value in text


def test_release_bundle_has_manifest_and_checksums():

    text = source()

    assert (
        "RELEASE_MANIFEST.txt"
        in text
    )

    assert (
        "SHA256SUMS"
        in text
    )

    assert (
        "sha256sum"
        in text
    )

    assert (
        "tar.gz"
        in text
    )


def test_release_bundle_audits_private_network_defaults():

    text = source()

    assert (
        "private IPv4 found in release bundle"
        in text
    )

    assert (
        "Wheel private-network audit: PASS"
        in text
    )


def test_release_bundle_does_not_copy_git_metadata():

    text = source()

    assert (
        "repository metadata found in release bundle"
        in text
    )

    assert (
        'cp -a "$ROOT/.git"'
        not in text
    )

    assert (
        "git archive"
        not in text
    )


def test_release_bundle_cleans_generated_build_directory():

    text = source()

    assert (
        'if [ -e "$ROOT/build" ]; then'
        in text
    )

    assert (
        "release bundle requires the source build/ "
        "directory to be absent"
        in text
    )

    assert (
        "cleanup_build_artifact()"
        in text
    )

    cleanup = (
        text
        .split(
            "cleanup_build_artifact() {",
            1,
        )[1]
        .split(
            "}",
            1,
        )[0]
    )

    assert (
        "rm -rf"
        in cleanup
    )

    assert (
        '"$ROOT/build"'
        in cleanup
    )

    assert (
        "trap cleanup_build_artifact EXIT"
        in text
    )


def test_release_artifact_directories_are_gitignored():

    gitignore = (
        ROOT
        / ".gitignore"
    ).read_text(
        encoding="utf-8"
    ).splitlines()

    values = {
        line.strip()
        for line in gitignore
    }

    assert "build/" in values
    assert "dist-release/" in values


def test_release_archive_checksum_is_portable():

    text = source()

    assert (
        'cd "$OUTPUT_ROOT"'
        in text
    )

    assert (
        '"$(basename "$ARCHIVE")"'
        in text
    )

    assert (
        '> "$(basename "$ARCHIVE_SUM")"'
        in text
    )

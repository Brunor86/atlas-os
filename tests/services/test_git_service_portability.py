from pathlib import Path

from atlas.services.git.service import (
    GitService,
)


def test_git_service_default_resolves_repository_root(
    monkeypatch,
):

    monkeypatch.delenv(
        "ATLAS_REPO_PATH",
        raising=False,
    )

    service = GitService()

    assert (
        service.path
        == Path(__file__)
        .resolve()
        .parents[2]
    )


def test_git_service_respects_repository_override(
    tmp_path,
    monkeypatch,
):

    repository = (
        tmp_path
        / "custom-atlas"
    )

    repository.mkdir()

    monkeypatch.setenv(
        "ATLAS_REPO_PATH",
        str(repository),
    )

    service = GitService()

    assert (
        service.path
        == repository.resolve()
    )


def test_git_service_missing_repository_fails_softly(
    tmp_path,
):

    missing = (
        tmp_path
        / "missing"
    )

    service = GitService(
        path=missing
    )

    assert (
        service.current_commit()
        is None
    )

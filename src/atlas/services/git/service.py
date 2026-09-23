import os
import subprocess
from pathlib import Path


def _default_repository_path() -> Path:
    """
    Resolve the ATLAS source repository without assuming a
    machine-specific installation path.

    ATLAS_REPO_PATH may explicitly override the location.

    For source/editable installations the package layout is:

        <repo>/src/atlas/services/git/service.py

    so parents[4] resolves to the repository root.
    """

    configured = str(
        os.getenv(
            "ATLAS_REPO_PATH",
            "",
        )
        or ""
    ).strip()

    if configured:
        return Path(
            configured
        ).expanduser().resolve()

    return (
        Path(__file__)
        .resolve()
        .parents[4]
    )


class GitService:

    def __init__(
        self,
        path=None,
    ):

        self.path = (
            Path(path).expanduser().resolve()
            if path is not None
            else _default_repository_path()
        )


    def run(
        self,
        command,
    ):

        try:

            result = subprocess.run(
                command,
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True,
            )

            return result.stdout.strip()


        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            OSError,
        ):

            return None



    def current_branch(
        self,
    ):

        return self.run(
            [
                "git",
                "branch",
                "--show-current",
            ]
        )



    def current_commit(
        self,
    ):

        return self.run(
            [
                "git",
                "rev-parse",
                "HEAD",
            ]
        )



    def last_commit(
        self,
    ):

        return self.run(
            [
                "git",
                "log",
                "-1",
                "--pretty=%h %s",
            ]
        )



    def recent_commits(
        self,
        limit=5,
    ):

        output = self.run(
            [
                "git",
                "log",
                f"-{limit}",
                "--pretty=%h|%ad|%s",
                "--date=short",
            ]
        )


        if not output:

            return []


        return [
            line
            for line in output.splitlines()
        ]



    def status(
        self,
    ):

        return self.run(
            [
                "git",
                "status",
                "--short",
            ]
        )



    def build_context(
        self,
    ):

        return {

            "branch":
                self.current_branch(),


            "commit":
                self.current_commit(),


            "last_commit":
                self.last_commit(),


            "recent_commits":
                self.recent_commits(),


            "status":
                self.status(),

        }

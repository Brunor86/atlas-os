import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from atlas.services.sentinel.contracts import (
    SentinelFinding,
    SentinelSeverity,
    SentinelState,
)


class SentinelStateStore:
    """
    Small durable state store for Sentinel deduplication.

    This is deliberately not another ATLAS database subsystem.

    One JSON document contains the most recent state for each
    Sentinel fingerprint. Writes are atomic.
    """

    VERSION = 1

    def __init__(
        self,
        path,
    ):
        self.path = Path(
            path
        )

    @staticmethod
    def _serialize_finding(
        finding,
    ):
        return {
            "fingerprint":
                finding.fingerprint,
            "source":
                finding.source,
            "kind":
                finding.kind,
            "subject":
                finding.subject,
            "severity":
                finding.severity.value,
            "state":
                finding.state.value,
            "title":
                finding.title,
            "summary":
                finding.summary,
            "observed_at":
                finding.observed_at.isoformat(),
            "evidence":
                dict(
                    finding.evidence
                ),
        }

    @staticmethod
    def _deserialize_finding(
        data,
    ):
        return SentinelFinding(
            fingerprint=str(
                data["fingerprint"]
            ),
            source=str(
                data["source"]
            ),
            kind=str(
                data["kind"]
            ),
            subject=str(
                data["subject"]
            ),
            severity=SentinelSeverity(
                data["severity"]
            ),
            state=SentinelState(
                data["state"]
            ),
            title=str(
                data["title"]
            ),
            summary=str(
                data["summary"]
            ),
            observed_at=datetime.fromisoformat(
                data["observed_at"]
            ),
            evidence=dict(
                data.get(
                    "evidence"
                )
                or {}
            ),
        )

    def load(
        self,
    ):
        if not self.path.exists():
            return {}

        data = json.loads(
            self.path.read_text()
        )

        if (
            data.get("version")
            != self.VERSION
        ):
            raise ValueError(
                "unsupported Sentinel state version"
            )

        findings = (
            data.get("findings")
            or {}
        )

        return {
            fingerprint:
                self._deserialize_finding(
                    finding
                )
            for fingerprint, finding
            in findings.items()
        }

    def save(
        self,
        state,
    ):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "version":
                self.VERSION,
            "findings": {
                fingerprint:
                    self._serialize_finding(
                        finding
                    )
                for fingerprint, finding
                in sorted(
                    state.items()
                )
            },
        }

        fd, temporary = tempfile.mkstemp(
            prefix=(
                f".{self.path.name}."
            ),
            dir=self.path.parent,
            text=True,
        )

        temporary_path = Path(
            temporary
        )

        try:
            with os.fdopen(
                fd,
                "w",
            ) as handle:
                json.dump(
                    payload,
                    handle,
                    indent=2,
                    sort_keys=True,
                    default=str,
                )

                handle.write(
                    "\n"
                )

                handle.flush()
                os.fsync(
                    handle.fileno()
                )

            os.chmod(
                temporary_path,
                0o600,
            )

            os.replace(
                temporary_path,
                self.path,
            )

        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        os.chmod(
            self.path,
            0o600,
        )

from dataclasses import dataclass

from atlas.core.asset import AssetStatus, health_from_status


@dataclass(slots=True)
class AssetHealthFinding:

    asset_id: str

    severity: str

    title: str

    message: str

    category: str

    def key(self):

        return (
            f"{self.asset_id}:"
            f"{self.category}:"
            f"{self.title}"
        )


class AssetHealthAnalyzer:

    def analyze(self, asset):

        findings = []

        for observation in asset.observations:

            if observation.type == "smart":

                if observation.value == "FAILED":

                    findings.append(
                        AssetHealthFinding(
                            asset_id=asset.id,
                            severity="CRITICAL",
                            title="SMART failure detected",
                            message=(
                                "Storage device SMART reports a failure condition"
                            ),
                            category="storage",
                        )
                    )

                elif observation.value == "UNAVAILABLE":

                    continue

            if observation.type == "temperature":

                try:
                    temperature = int(observation.value)

                except Exception:
                    continue

                if temperature >= 60:

                    findings.append(
                        AssetHealthFinding(
                            asset_id=asset.id,
                            severity="CRITICAL",
                            title="High storage temperature",
                            message=(
                                f"Storage temperature is {temperature}C"
                            ),
                            category="temperature",
                        )
                    )

                elif temperature >= 50:

                    findings.append(
                        AssetHealthFinding(
                            asset_id=asset.id,
                            severity="WARNING",
                            title="Elevated storage temperature",
                            message=(
                                f"Storage temperature is {temperature}C"
                            ),
                            category="temperature",
                        )
                    )

        return findings

    def evaluate_health(self, asset, findings=None):

        baseline = health_from_status(
            asset.status
        )

        if findings is None:
            findings = self.analyze(asset)

        health = baseline

        for finding in findings:

            severity = finding.severity.upper()

            if severity == "CRITICAL":

                health = min(
                    health,
                    0.0,
                )

            elif severity == "WARNING":

                health = min(
                    health,
                    60.0,
                )

        return max(
            0.0,
            min(
                100.0,
                health,
            ),
        )

    def evaluate(self, asset):

        findings = self.analyze(asset)

        health = self.evaluate_health(
            asset,
            findings,
        )

        asset.health = health

        return findings

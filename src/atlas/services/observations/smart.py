from atlas.core.observation import Observation


class SmartObservationBuilder:

    def build(self, asset_id, smart):

        observations = []

        if smart.temperature is not None:

            severity = "INFO"

            if smart.temperature >= 50:
                severity = "WARNING"

            if smart.temperature >= 60:
                severity = "CRITICAL"

            observations.append(
                Observation(
                    asset_id=asset_id,
                    type="temperature",
                    value=smart.temperature,
                    severity=severity,
                    source="smart",
                )
            )

        if smart.smart_available:

            if smart.smart_passed:

                observations.append(
                    Observation(
                        asset_id=asset_id,
                        type="smart",
                        value="PASSED",
                        severity="INFO",
                        source="smart",
                    )
                )

            else:

                observations.append(
                    Observation(
                        asset_id=asset_id,
                        type="smart",
                        value="FAILED",
                        severity="CRITICAL",
                        source="smart",
                    )
                )

        else:

            observations.append(
                Observation(
                    asset_id=asset_id,
                    type="smart",
                    value="UNAVAILABLE",
                    severity="INFO",
                    source="smart",
                )
            )

        return observations

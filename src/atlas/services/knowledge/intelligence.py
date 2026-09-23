
class KnowledgeIntelligenceAnalyzer:


    def analyze(
        self,
        card,
    ):

        risk = 0

        warnings = []

        recommendations = []


        #
        # Role analysis
        #

        roles = set(
            card.roles
        )


        if "DOCKER_HOST" in roles:

            risk += 40

            warnings.append(
                "Docker runtime host"
            )

            recommendations.append(
                "Check docker.service and container health"
            )



        if "DATABASE_SERVER" in roles:

            risk += 30

            warnings.append(
                "Database infrastructure"
            )

            recommendations.append(
                "Verify database availability and storage"
            )



        if "MONITORING_NODE" in roles:

            risk += 15

            warnings.append(
                "Monitoring dependency"
            )

            recommendations.append(
                "Verify monitoring pipeline"
            )



        if "MEDIA_SERVER" in roles:

            risk += 10

            warnings.append(
                "Media workload provider"
            )



        #
        # Relationship intelligence
        #

        if card.relationship_count > 20:

            risk += 20

            warnings.append(
                "High relationship density"
            )

            recommendations.append(
                "Review dependency graph before changes"
            )



        #
        # Blast radius
        #

        blast = (

            len(card.dependents)

            +

            len(card.dependencies)

        )


        card.blast_radius = blast



        if blast > 10:

            warnings.append(
                f"Large blast radius ({blast})"
            )



        #
        # Final risk
        #

        card.risk_score = min(
            risk,
            100
        )



        #
        # Operational summary
        #

        summary = []

        summary.append(
            f"{card.asset_name} "
            f"is a {card.asset_type}"
        )


        summary.append(
            f"risk {card.risk_score}/100"
        )


        if blast:

            summary.append(
                f"with {blast} relationships"
            )


        card.operational_summary = (
            " ".join(summary)
        )



        card.observations.extend(
            warnings
        )


        card.impact_reasons = list(
            dict.fromkeys(
                warnings
            )
        )


        card.recommendations = recommendations


        return card

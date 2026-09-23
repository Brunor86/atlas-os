class EventRule:
    """
    Convert persisted operational events into NOC signals.

    ATLAS currently receives events from two lifecycle domains:

        persisted EventService events:
            open / closed

        in-memory Health projection events:
            active

    Both "open" and "active" represent a currently applicable
    event. Event severity determines whether that event represents
    an operational problem.

    Informational events remain useful history/context but must
    never increase the NOC operational score.
    """

    _ACTIVE_STATUSES = {
        "open",
        "active",
    }

    _IMPACT = {
        "warning": 35,
        "critical": 60,
    }


    def evaluate(
        self,
        events,
    ):

        signals = []

        if not events:
            return signals


        for event in events:

            status = str(
                getattr(
                    event,
                    "status",
                    "",
                )
                or ""
            ).strip().lower()

            if status not in self._ACTIVE_STATUSES:
                continue


            severity = str(
                getattr(
                    event,
                    "severity",
                    "warning",
                )
                or "warning"
            ).strip().lower()


            #
            # Informational observations such as
            # "Infrastructure Healthy" or
            # "All containers are running" are deliberately
            # persisted as open events while current, but they
            # are not faults and must not affect NOC scoring.
            #
            if severity not in self._IMPACT:
                continue


            signals.append(
                {
                    "source":
                        "event",

                    "impact":
                        self._IMPACT[
                            severity
                        ],

                    "severity":
                        severity,

                    "message":
                        (
                            f"{event.title}: "
                            f"{event.message}"
                        ),

                    "asset_id":
                        getattr(
                            event,
                            "asset_id",
                            None,
                        ),
                }
            )


        return signals

import logging


def get_logger(
    name: str,
) -> logging.Logger:

    logger = logging.getLogger(
        f"atlas.{name}"
    )

    if not logger.handlers:

        handler = logging.StreamHandler()

        formatter = logging.Formatter(
            (
                "%(asctime)s | %(levelname)s | "
                "%(name)s | %(message)s"
            )
        )

        handler.setFormatter(
            formatter
        )

        logger.addHandler(
            handler
        )

    #
    # Let the application's root logging level decide whether
    # DEBUG/INFO records are emitted.
    #
    # The logger owns its handler, therefore propagation must be
    # disabled or every message is emitted twice when the worker
    # also configures the root logger.
    #
    logger.setLevel(
        logging.NOTSET
    )

    logger.propagate = False

    return logger

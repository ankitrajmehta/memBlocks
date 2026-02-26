"""memblocks.logger — library-safe logging setup.

- Applications that use memBlocks are free to configure the ``memblocks``
  logger however they wish:

    import logging
    logging.getLogger("memblocks").setLevel(logging.DEBUG)
    logging.getLogger("memblocks").addHandler(logging.StreamHandler())

Logger hierarchy
----------------
All loggers in the library follow the ``memblocks.<module>`` naming scheme,
which means they are children of the top-level ``memblocks`` logger and inherit
its handlers/level automatically.

Usage inside the library
-------------------------
    from memblocks.logger import get_logger
    logger = get_logger(__name__)
    logger.debug("Connecting to Qdrant at %s:%s", host, port)
    logger.info("Created block %s", block_id)
    logger.warning("Arize monitoring disabled — keys not set")
    logger.error("Failed to store vector: %s", exc)
"""

import logging

# ── Top-level library logger ─────────────────────────────────────────────────
# All child loggers (memblocks.storage.mongo, memblocks.services.session, …)
# propagate to this one. Applications control output by configuring this logger.
_root_logger = logging.getLogger("memblocks")
_root_logger.addHandler(logging.NullHandler())


def get_logger(name: str) -> logging.Logger:
    """Return a child logger for *name*.

    Intended to be called at module level::

        from memblocks.logger import get_logger
        logger = get_logger(__name__)

    Because every memblocks module is under the ``memblocks`` package,
    ``__name__`` always produces a logger such as
    ``memblocks.services.session`` that is a child of the root
    ``memblocks`` logger, so handler/level configuration propagates
    automatically.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)


__all__ = ["get_logger"]

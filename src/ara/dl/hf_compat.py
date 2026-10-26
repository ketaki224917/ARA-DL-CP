"""Hugging Face runtime compatibility helpers."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
_SYSTEM_CERTS_CONFIGURED = False


def configure_system_certificates() -> None:
    """Use platform trust roots for Hugging Face requests when truststore is installed.

    On hosts whose Python certifi bundle omits the trusted system root, Hugging Face
    downloads otherwise fail TLS verification. This keeps verification enabled while
    allowing the operating system's configured roots to be used.
    """
    global _SYSTEM_CERTS_CONFIGURED
    if _SYSTEM_CERTS_CONFIGURED:
        return
    try:
        import truststore
    except ImportError:
        logger.debug("truststore is unavailable; retaining the Python default CA bundle")
    else:
        truststore.inject_into_ssl()
        logger.debug("Enabled platform certificate roots for model downloads")
    _SYSTEM_CERTS_CONFIGURED = True

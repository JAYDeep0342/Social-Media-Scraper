"""Shared, production-grade async HTTP client: connection pooling/reuse,
configurable timeouts, optional HTTP/2 (falls back to HTTP/1.1 if the
optional `h2` package isn't installed), and a graceful close.

No retry, rate limiting, or circuit breaking here — those are separate,
composable modules that `SessionManager` wires around this client.
"""

import ssl
from typing import Any, Mapping, MutableMapping, Optional, Sequence

import httpx

from app.config.http_config import http_config
from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

EventHooks = MutableMapping[str, Sequence[Any]]

# httpx defaults to verifying against certifi's static CA bundle, which
# lacks intermediates some sites (e.g. DuckDuckGo's html endpoint) omit
# from their handshake -- verification then fails with "unable to get
# local issuer certificate" even though the site's cert is valid. The
# platform default context (OS trust store, with Windows' automatic
# intermediate-cert fetching) verifies the same chains browsers do, so use
# it instead of the certifi-only default.
_SSL_CONTEXT = ssl.create_default_context()


class HTTPClientManager:
    """Owns a single shared httpx.AsyncClient for the process lifetime."""

    def __init__(
        self,
        *,
        http2: Optional[bool] = None,
        headers: Optional[Mapping[str, str]] = None,
        event_hooks: Optional[EventHooks] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        settings = get_settings()

        limits = httpx.Limits(
            max_connections=settings.CONNECTION_POOL_SIZE,
            max_keepalive_connections=settings.CONNECTION_POOL_SIZE_PER_HOST,
        )
        timeout = httpx.Timeout(
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
            connect=settings.CONNECT_TIMEOUT_SECONDS,
        )
        merged_headers = dict(http_config.default_headers)
        if headers:
            merged_headers.update(headers)

        self._client = self._build_client(
            http2=settings.HTTP2_ENABLED if http2 is None else http2,
            limits=limits,
            timeout=timeout,
            headers=merged_headers,
            event_hooks=event_hooks,
            transport=transport,
        )

    @staticmethod
    def _build_client(
        *,
        http2: bool,
        limits: httpx.Limits,
        timeout: httpx.Timeout,
        headers: Mapping[str, str],
        event_hooks: Optional[EventHooks],
        transport: Optional[httpx.AsyncBaseTransport],
    ) -> httpx.AsyncClient:
        kwargs: dict[str, Any] = dict(
            limits=limits,
            timeout=timeout,
            headers=headers,
            event_hooks=event_hooks or {},
        )
        if transport is not None:
            kwargs["transport"] = transport
        else:
            kwargs["verify"] = _SSL_CONTEXT

        try:
            return httpx.AsyncClient(http2=http2, **kwargs)
        except ImportError:
            logger.warning(
                "HTTP/2 requested but the 'h2' package is not installed; falling back to HTTP/1.1"
            )
            return httpx.AsyncClient(http2=False, **kwargs)

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client

    @property
    def is_closed(self) -> bool:
        return self._client.is_closed

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        return await self._client.request(method, url, **kwargs)

    async def aclose(self) -> None:
        if not self._client.is_closed:
            await self._client.aclose()

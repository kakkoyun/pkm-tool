"""Google Docs integration."""

import os
from datetime import date, datetime
from typing import Any

import httpx
import structlog

from pkm_tool.auth import AuthManager
from pkm_tool.auth.oauth import GoogleOAuthProvider
from pkm_tool.cache import get_cached_client
from pkm_tool.config import CacheConfig
from pkm_tool.models import GoogleDoc

logger = structlog.get_logger(__name__)
_AUTH_MANAGER = AuthManager()


def fetch_google_docs(
    target_date: date,
    config: dict[str, Any],
    cache_config: CacheConfig | None = None,
) -> list[GoogleDoc]:
    """
    Fetch Google Docs opened on target date.

    Note: This requires Google Drive API access and OAuth2 setup.
    This is a placeholder implementation.

    Args:
        target_date: Date to fetch docs for
        config: Configuration dictionary with OAuth credentials
        cache_config: Optional cache configuration for HTTP response caching

    Returns:
        List of GoogleDoc objects
    """
    logger.debug("google_docs_fetch_started", date=str(target_date))
    access_token = None
    provider = _build_provider(config)

    if provider:
        token = _AUTH_MANAGER.ensure_oauth_token("google_docs", provider, allow_interactive=False)
        if token:
            access_token = token.token

    if access_token is None:
        access_token = _get_google_docs_token(config)

    if not access_token:
        logger.warning("google_docs_no_token", message="No Google Docs access token configured")
        return []

    docs: list[GoogleDoc] = []

    try:
        logger.debug("google_docs_querying_drive_api", date=str(target_date))
        headers = {"Authorization": f"Bearer {access_token}"}

        # Use cached client if cache config provided, otherwise regular httpx client
        if cache_config:
            client = get_cached_client(cache_config, headers=headers, timeout=30.0)
        else:
            client = httpx.Client(headers=headers, timeout=30.0)

        with client:
            # Query Drive API for recently opened docs
            # Note: Google Drive API doesn't directly track "opened" events
            # This queries for modified/viewed files instead

            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())

            # Query for Google Docs modified on target date
            mime_type = "mimeType='application/vnd.google-apps.document'"
            start_time = f"modifiedTime >= '{start_datetime.isoformat()}Z'"
            end_time = f"modifiedTime <= '{end_datetime.isoformat()}Z'"
            query = f"{mime_type} and {start_time} and {end_time}"

            response = client.get(
                "https://www.googleapis.com/drive/v3/files",
                params={
                    "q": query,
                    "fields": "files(id,name,webViewLink,modifiedTime,mimeType)",
                    "orderBy": "modifiedTime desc",
                },
            )
            response.raise_for_status()
            data = response.json()

            for file in data.get("files", []):
                doc_type = "document"
                if "spreadsheet" in file.get("mimeType", ""):
                    doc_type = "spreadsheet"
                elif "presentation" in file.get("mimeType", ""):
                    doc_type = "presentation"

                doc = GoogleDoc(
                    title=file["name"],
                    url=file["webViewLink"],
                    opened_at=datetime.fromisoformat(file["modifiedTime"].replace("Z", "+00:00")),
                    doc_type=doc_type,
                )
                docs.append(doc)

        logger.info("google_docs_fetched", doc_count=len(docs))

    except (httpx.HTTPError, KeyError) as e:
        # All exceptions are caught and return empty list
        # This ensures graceful degradation
        logger.error("google_docs_fetch_failed", error=str(e), exc_info=True)

    return docs


def _get_google_docs_token(config: dict[str, Any]) -> str | None:
    """Retrieve Google Docs access token from config or environment."""
    return config.get("access_token", os.environ.get("GOOGLE_ACCESS_TOKEN"))


def _build_provider(config: dict[str, Any]) -> GoogleOAuthProvider | None:
    client_id = config.get("client_id") or os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        return None
    client_secret = config.get("client_secret") or os.environ.get("GOOGLE_CLIENT_SECRET")
    scopes = config.get("scopes") or ["https://www.googleapis.com/auth/drive.readonly"]
    if isinstance(scopes, str):
        scopes = [scopes]
    return GoogleOAuthProvider(client_id, client_secret=client_secret, scopes=scopes)

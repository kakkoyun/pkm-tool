"""Google Docs integration."""

import os
from datetime import date, datetime
from typing import Any

import httpx

from pkm_tool.models import GoogleDoc


def fetch_google_docs(target_date: date, config: dict[str, Any]) -> list[GoogleDoc]:
    """
    Fetch Google Docs opened on target date.

    Note: This requires Google Drive API access and OAuth2 setup.
    This is a placeholder implementation.

    Args:
        target_date: Date to fetch docs for
        config: Configuration dictionary with OAuth credentials

    Returns:
        List of GoogleDoc objects
    """
    access_token = config.get("access_token", os.environ.get("GOOGLE_ACCESS_TOKEN"))

    if not access_token:
        return []

    docs = []

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        with httpx.Client(headers=headers, timeout=30.0) as client:
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

    except (httpx.HTTPError, KeyError):
        pass

    return docs

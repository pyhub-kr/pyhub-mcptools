"""Google Drive API async helper using aiohttp.

This module provides async access to Google Drive API for listing
and searching spreadsheets.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from .auth import get_credentials
from .constants import DRIVE_API_BASE_URL, SPREADSHEET_MIME_TYPE
from .exceptions import AuthenticationError, GoogleSheetsError, RateLimitError

logger = logging.getLogger(__name__)


class GoogleDriveAsyncClient:
    """Async client for Google Drive API v3."""

    BASE_URL = DRIVE_API_BASE_URL
    SPREADSHEET_MIME_TYPE = SPREADSHEET_MIME_TYPE

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._credentials: Optional[Credentials] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        if not self._credentials:
            self._credentials = get_credentials()

        # Refresh token if needed
        if self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(None)
            except RefreshError as e:
                raise AuthenticationError("Failed to refresh authentication token") from e

        return {
            "Authorization": f"Bearer {self._credentials.token}",
            "Accept": "application/json",
        }

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle API response and errors."""
        text = await response.text()

        if response.status == 200:
            return await response.json()

        # Handle error responses
        try:
            error_data = await response.json()
            error = error_data.get("error", {})
            message = error.get("message", text)
        except Exception:
            message = text

        if response.status == 401:
            raise AuthenticationError(f"Authentication failed: {message}")
        elif response.status == 403:
            if "quotaExceeded" in text or "rateLimitExceeded" in text:
                raise RateLimitError(f"API rate limit exceeded: {message}")
            else:
                raise GoogleSheetsError(f"Permission denied: {message}")
        elif response.status == 404:
            raise GoogleSheetsError(f"Resource not found: {message}")
        else:
            raise GoogleSheetsError(f"API error (status {response.status}): {message}")

    async def list_spreadsheets(
        self, page_size: int = 100, page_token: Optional[str] = None, order_by: str = "modifiedTime desc"
    ) -> Dict[str, Any]:
        """List all spreadsheets accessible by the user.

        Args:
            page_size: Number of files to return per page (max 1000)
            page_token: Token for retrieving next page
            order_by: Sort order (e.g., "modifiedTime desc")

        Returns:
            Dict containing:
            - files: List of spreadsheet metadata
            - nextPageToken: Token for next page (if available)
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Use async with statement.")

        # Build query for spreadsheets only
        query = f"mimeType='{self.SPREADSHEET_MIME_TYPE}' and trashed=false"

        params = {
            "q": query,
            "pageSize": min(page_size, 1000),
            "orderBy": order_by,
            "fields": "nextPageToken,files(id,name,createdTime,modifiedTime,owners,shared)",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }

        if page_token:
            params["pageToken"] = page_token

        url = f"{self.BASE_URL}/files"
        headers = self._get_headers()

        async with self._session.get(url, headers=headers, params=params) as response:
            data = await self._handle_response(response)

            # Transform files data
            files = []
            for file in data.get("files", []):
                files.append(
                    {
                        "id": file["id"],
                        "name": file["name"],
                        "url": f"https://docs.google.com/spreadsheets/d/{file['id']}",
                        "createdTime": file.get("createdTime", ""),
                        "modifiedTime": file.get("modifiedTime", ""),
                        "owners": [owner.get("emailAddress", "") for owner in file.get("owners", [])],
                        "shared": file.get("shared", False),
                    }
                )

            return {
                "files": files,
                "nextPageToken": data.get("nextPageToken"),
            }

    async def list_all_spreadsheets(self, max_results: int = 1000) -> List[Dict[str, Any]]:
        """List all spreadsheets (handles pagination automatically).

        Args:
            max_results: Maximum number of results to return

        Returns:
            List of all spreadsheet metadata
        """
        all_files = []
        page_token = None

        while len(all_files) < max_results:
            page_size = min(100, max_results - len(all_files))
            result = await self.list_spreadsheets(page_size=page_size, page_token=page_token)

            all_files.extend(result["files"])
            page_token = result.get("nextPageToken")

            if not page_token:
                break

            # Log progress for large lists
            if len(all_files) > 0 and len(all_files) % 500 == 0:
                logger.info(f"Retrieved {len(all_files)} spreadsheets so far...")

        return all_files[:max_results]

    async def search_spreadsheets(
        self,
        search_term: str,
        exact_match: bool = False,
        in_name: bool = True,
        in_content: bool = False,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search for spreadsheets by name or content.

        Args:
            search_term: Term to search for
            exact_match: Whether to match exactly (only for name search)
            in_name: Search in file names
            in_content: Search in file content (slower)
            max_results: Maximum results to return

        Returns:
            List of matching spreadsheet metadata
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Use async with statement.")

        # Build search query
        query_parts = [f"mimeType='{self.SPREADSHEET_MIME_TYPE}'", "trashed=false"]

        if in_name:
            if exact_match:
                query_parts.append(f"name='{search_term}'")
            else:
                query_parts.append(f"name contains '{search_term}'")

        if in_content and not exact_match:
            query_parts.append(f"fullText contains '{search_term}'")

        query = " and ".join(query_parts)

        params = {
            "q": query,
            "pageSize": min(max_results, 1000),
            "orderBy": "modifiedTime desc",
            "fields": "files(id,name,createdTime,modifiedTime,owners,shared)",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }

        url = f"{self.BASE_URL}/files"
        headers = self._get_headers()

        async with self._session.get(url, headers=headers, params=params) as response:
            data = await self._handle_response(response)

            # Transform files data
            files = []
            for file in data.get("files", []):
                files.append(
                    {
                        "id": file["id"],
                        "name": file["name"],
                        "url": f"https://docs.google.com/spreadsheets/d/{file['id']}",
                        "createdTime": file.get("createdTime", ""),
                        "modifiedTime": file.get("modifiedTime", ""),
                        "owners": [owner.get("emailAddress", "") for owner in file.get("owners", [])],
                        "shared": file.get("shared", False),
                    }
                )

            return files

    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get metadata for a specific file.

        Args:
            file_id: Google Drive file ID

        Returns:
            File metadata dictionary
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Use async with statement.")

        url = f"{self.BASE_URL}/files/{quote(file_id)}"
        headers = self._get_headers()
        params = {
            "fields": "id,name,mimeType,createdTime,modifiedTime,owners,shared,permissions",
            "supportsAllDrives": "true",
        }

        async with self._session.get(url, headers=headers, params=params) as response:
            return await self._handle_response(response)

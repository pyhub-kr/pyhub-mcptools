"""Google Sheets 비동기 API 클라이언트

gspread-asyncio를 사용한 진정한 비동기 구현입니다.
- 완전한 비동기 처리
- 자동 재시도 및 rate limiting
- 객체 캐싱
- 자동 토큰 갱신
"""

import logging
import re
from functools import wraps
from typing import Any, Callable, Optional

import gspread_asyncio
from django.conf import settings
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound

from .auth import get_credentials as get_sync_credentials
from .constants import ErrorPatterns
from .exceptions import AuthenticationError, GoogleSheetsError, RateLimitError, SpreadsheetNotFoundError

logger = logging.getLogger(__name__)


def handle_api_errors(func: Callable) -> Callable:
    """Decorator to handle API errors consistently across all client methods"""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            await self._handle_api_error(e)

    return wrapper


class GoogleSheetsAsyncClient:
    """Google Sheets 비동기 API 클라이언트"""

    def __init__(self):
        self.agcm: Optional[gspread_asyncio.AsyncioGspreadClientManager] = None
        self.max_retries = getattr(settings, "GOOGLE_SHEETS_MAX_RETRIES", 5)
        self._initialized = False

    def _get_credentials_func(self) -> Credentials:
        """gspread-asyncio용 credentials 함수"""
        try:
            return get_sync_credentials()
        except Exception as e:
            logger.error(f"Failed to get credentials: {e}")
            raise AuthenticationError(f"인증 정보를 가져올 수 없습니다: {e}") from e

    async def _ensure_initialized(self):
        """클라이언트 매니저 초기화 (이벤트 루프 감지 및 locale 고정 포함)"""
        import asyncio

        # 현재 이벤트 루프 확인
        current_loop = asyncio.get_running_loop()

        # 이벤트 루프가 변경되었거나 초기화되지 않은 경우 재초기화
        if not self._initialized or (hasattr(self, "_loop") and self._loop != current_loop):
            if hasattr(self, "_loop") and self._loop != current_loop:
                logger.debug("Event loop changed, reinitializing client manager")
                self._initialized = False
                self.agcm = None

            # 현재 이벤트 루프 저장
            self._loop = current_loop

            # gspread_asyncio 매니저 생성
            self.agcm = gspread_asyncio.AsyncioGspreadClientManager(self._get_credentials_func)

            # 영어 locale로 고정하기 위해 HTTP 세션 헤더 설정
            try:
                agc = await self.agcm.authorize()
                if hasattr(agc, "_http_client") and hasattr(agc._http_client, "session"):
                    agc._http_client.session.headers.update(
                        {"Accept-Language": "en-US,en;q=0.9", "Content-Language": "en-US"}
                    )
                    logger.debug("Set English locale headers for Google API requests")
            except Exception as e:
                logger.warning(f"Failed to set locale headers: {e}")

            self._initialized = True

    async def _handle_api_error(self, e: Exception):
        """API 에러 처리 (locale 독립적)"""
        if isinstance(e, RefreshError):
            raise AuthenticationError("Authentication token refresh failed. Please login again.")
        elif isinstance(e, SpreadsheetNotFound):
            raise SpreadsheetNotFoundError(f"Requested resource not found: {e}")
        elif isinstance(e, APIError):
            error_text = str(e)

            # HTTP 상태 코드 기반 우선 처리
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code

                if status_code == 403:
                    # 403 에러의 세부 구분
                    if ErrorPatterns.matches_pattern(error_text, ErrorPatterns.PERMISSION_KEYWORDS):
                        raise GoogleSheetsError(f"Permission denied: {e}")
                    elif ErrorPatterns.matches_pattern(error_text, ErrorPatterns.QUOTA_KEYWORDS):
                        raise RateLimitError(f"API quota exceeded: {e}")
                    else:
                        raise GoogleSheetsError(f"Access forbidden: {e}")

                elif status_code == 429:
                    raise RateLimitError(f"Rate limit exceeded: {e}")

                elif status_code == 404:
                    raise SpreadsheetNotFoundError(f"Resource not found: {e}")

                elif status_code == 401:
                    raise AuthenticationError(f"Authentication failed: {e}")

                elif status_code == 400:
                    raise GoogleSheetsError(f"Bad request: {e}")

            # 키워드 기반 폴백 처리 (상태 코드가 없는 경우)
            if ErrorPatterns.matches_pattern(error_text, ErrorPatterns.PERMISSION_KEYWORDS):
                raise GoogleSheetsError(f"Permission denied: {e}")
            elif ErrorPatterns.matches_pattern(error_text, ErrorPatterns.QUOTA_KEYWORDS):
                raise RateLimitError(f"API quota exceeded: {e}")
            elif ErrorPatterns.matches_pattern(error_text, ErrorPatterns.NOT_FOUND_KEYWORDS):
                raise SpreadsheetNotFoundError(f"Resource not found: {e}")
            elif ErrorPatterns.matches_pattern(error_text, ErrorPatterns.AUTHENTICATION_KEYWORDS):
                raise AuthenticationError(f"Authentication failed: {e}")
            else:
                raise GoogleSheetsError(f"Google API error: {e}")
        else:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise GoogleSheetsError(f"Operation failed: {e}")

    @handle_api_errors
    async def list_spreadsheets(self) -> list[dict[str, Any]]:
        """사용자가 접근 가능한 모든 스프레드시트 목록 반환"""
        from .drive_async import GoogleDriveAsyncClient

        async with GoogleDriveAsyncClient() as drive_client:
            spreadsheets = await drive_client.list_all_spreadsheets(max_results=1000)
            return spreadsheets

    @handle_api_errors
    async def search_spreadsheets(self, search_term: str, exact_match: bool = False) -> list[dict[str, Any]]:
        """이름으로 스프레드시트 검색"""
        from .drive_async import GoogleDriveAsyncClient

        async with GoogleDriveAsyncClient() as drive_client:
            matches = await drive_client.search_spreadsheets(
                search_term=search_term, exact_match=exact_match, max_results=100
            )
            return matches

    @handle_api_errors
    async def create_spreadsheet(self, name: str) -> dict[str, Any]:
        """새 스프레드시트 생성 (첫 번째 시트를 'Sheet1'로 표준화)"""
        await self._ensure_initialized()

        agc = await self.agcm.authorize()
        spreadsheet = await agc.create(name)

        # Try to standardize the first sheet name to "Sheet1"
        try:
            worksheets = await spreadsheet.worksheets()
            if worksheets:
                first_sheet = worksheets[0]
                if first_sheet.title != "Sheet1":
                    logger.info(f"Renaming default sheet from '{first_sheet.title}' to 'Sheet1'")
                    await first_sheet.update_title("Sheet1")
        except Exception as e:
            logger.warning(f"Failed to standardize first sheet name: {e}")

        return {
            "id": spreadsheet.id,
            "name": spreadsheet.title,
            "url": spreadsheet.url,
        }

    @handle_api_errors
    async def get_spreadsheet(self, spreadsheet_id: str):
        """스프레드시트 객체 반환"""
        await self._ensure_initialized()

        agc = await self.agcm.authorize()
        return await agc.open_by_key(spreadsheet_id)

    @handle_api_errors
    async def get_spreadsheet_info(self, spreadsheet_id: str) -> dict[str, Any]:
        """스프레드시트 정보 반환"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)

        sheets_info = []
        worksheets = await spreadsheet.worksheets()

        for sheet in worksheets:
            sheets_info.append(
                {
                    "id": sheet.id,
                    "name": sheet.title,
                    "index": sheet.index,
                    "rowCount": sheet.row_count,
                    "columnCount": sheet.col_count,
                }
            )

        return {
            "id": spreadsheet.id,
            "name": spreadsheet.title,
            "url": spreadsheet.url,
            "sheets": sheets_info,
        }

    def _parse_cell_address(self, cell_str: str) -> tuple[int, int]:
        """셀 주소를 행/열 인덱스로 변환 (예: A1 -> (0, 0))"""
        match = re.match(r"^([A-Z]+)(\d+)$", cell_str)
        if not match:
            raise ValueError(f"Invalid cell address: {cell_str}")

        col_str, row_str = match.groups()
        row = int(row_str) - 1  # 0-based
        col = sum((ord(c) - ord("A") + 1) * (26**i) for i, c in enumerate(reversed(col_str))) - 1

        return row, col

    def _trim_empty_rows_and_cols(self, values: list[list[Any]]) -> list[list[Any]]:
        """빈 행과 열 제거"""
        if not values:
            return []

        # 빈 행 제거 (끝에서부터)
        while values and all(cell == "" for cell in values[-1]):
            values.pop()

        if not values:
            return []

        # 빈 열 제거 (오른쪽부터)
        max_col = 0
        for row in values:
            for i in range(len(row) - 1, -1, -1):
                if row[i] != "":
                    max_col = max(max_col, i + 1)
                    break

        # 각 행을 최대 열까지만 유지
        trimmed = []
        for row in values:
            trimmed.append(row[:max_col] if len(row) > max_col else row)

        return trimmed

    def _expand_from_cell(
        self, all_values: list[list[Any]], start_row: int, start_col: int, mode: str
    ) -> list[list[Any]]:
        """시작 셀에서 지정된 모드로 확장"""
        if not all_values or start_row >= len(all_values):
            return []

        if mode == "table":
            # 연속된 데이터 블록 찾기
            end_row = start_row
            end_col = start_col

            # 오른쪽으로 확장 (헤더 찾기)
            if start_row < len(all_values) and start_col < len(all_values[start_row]):
                row = all_values[start_row]
                for col in range(start_col, len(row)):
                    if row[col] == "":
                        break
                    end_col = col

            # 아래로 확장
            for row_idx in range(start_row, len(all_values)):
                # 첫 번째 열이 비어있으면 중단
                if start_col >= len(all_values[row_idx]) or all_values[row_idx][start_col] == "":
                    break
                end_row = row_idx

            # 추출
            result = []
            for row_idx in range(start_row, end_row + 1):
                row_data = []
                for col_idx in range(start_col, min(end_col + 1, len(all_values[row_idx]))):
                    row_data.append(all_values[row_idx][col_idx])
                result.append(row_data)

            return result

        elif mode == "down":
            # 아래로만 확장
            result = []
            for row_idx in range(start_row, len(all_values)):
                if start_col >= len(all_values[row_idx]) or all_values[row_idx][start_col] == "":
                    break
                result.append([all_values[row_idx][start_col]])
            return result

        elif mode == "right":
            # 오른쪽으로만 확장
            if start_row >= len(all_values):
                return []
            row = all_values[start_row]
            result_row = []
            for col_idx in range(start_col, len(row)):
                if row[col_idx] == "":
                    break
                result_row.append(row[col_idx])
            return [result_row] if result_row else []

        return []

    def _resolve_sheet_reference(self, sheet_name: str, worksheets: list) -> str:
        """Resolve sheet reference by name or index (e.g., '0' -> first sheet name)"""
        # Check if it's a numeric index
        if sheet_name.isdigit():
            index = int(sheet_name)
            if 0 <= index < len(worksheets):
                return worksheets[index].title
            else:
                raise ValueError(f"Sheet index {index} is out of range (0-{len(worksheets)-1})")

        # Return as-is if it's a sheet name
        return sheet_name

    @handle_api_errors
    async def get_values(
        self, spreadsheet_id: str, sheet_name: str, range_str: Optional[str] = None, expand_mode: Optional[str] = None
    ) -> list[list[Any]]:
        """셀 범위의 값 반환 (expand 모드 지원, 인덱스 기반 시트 참조 지원)"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        worksheets = await spreadsheet.worksheets()

        # Resolve sheet reference (by name or index)
        resolved_sheet_name = self._resolve_sheet_reference(sheet_name, worksheets)
        sheet = await spreadsheet.worksheet(resolved_sheet_name)

        if expand_mode and range_str:
            # Expand 모드일 때는 전체 데이터를 가져와서 처리
            all_values = await sheet.get_all_values()

            # 시작 셀 파싱
            if ":" in range_str:
                range_str = range_str.split(":")[0]

            try:
                start_row, start_col = self._parse_cell_address(range_str)
                return self._expand_from_cell(all_values, start_row, start_col, expand_mode)
            except ValueError:
                # 잘못된 범위 형식이면 일반 모드로 처리
                values = await sheet.get_values(range_str) if range_str else await sheet.get_all_values()
                return self._trim_empty_rows_and_cols(values) if expand_mode == "table" else values
        else:
            # 일반 모드
            if range_str:
                values = await sheet.get_values(range_str)
            else:
                values = await sheet.get_all_values()
            return values

    @handle_api_errors
    async def set_values(
        self, spreadsheet_id: str, sheet_name: str, range_str: str, values: list[list[Any]]
    ) -> dict[str, Any]:
        """셀 범위에 값 설정 (인덱스 기반 시트 참조 지원)"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        worksheets = await spreadsheet.worksheets()

        # Resolve sheet reference (by name or index)
        resolved_sheet_name = self._resolve_sheet_reference(sheet_name, worksheets)

        try:
            sheet = await spreadsheet.worksheet(resolved_sheet_name)
        except Exception as e:
            logger.error(f"Failed to get worksheet '{resolved_sheet_name}': {e}")
            # 더 구체적인 에러 메시지 제공
            if ErrorPatterns.matches_pattern(str(e), ErrorPatterns.NOT_FOUND_KEYWORDS):
                raise SpreadsheetNotFoundError(f"Worksheet '{resolved_sheet_name}' not found in spreadsheet") from e
            else:
                raise GoogleSheetsError(f"Failed to access worksheet '{resolved_sheet_name}': {e}") from e

        # gspread-asyncio는 2D 배열 필요
        if not values:
            values = [[]]
        elif not isinstance(values[0], list):
            # 1D 배열인 경우 2D로 변환
            values = [values]

        result = await sheet.update(range_str, values, value_input_option="USER_ENTERED")

        return {
            "updatedCells": result.get("updatedCells", 0),
            "updatedRows": result.get("updatedRows", 0),
            "updatedColumns": result.get("updatedColumns", 0),
            "updatedRange": result.get("updatedRange", range_str),
        }

    @handle_api_errors
    async def clear_values(self, spreadsheet_id: str, sheet_name: str, range_str: str) -> dict[str, Any]:
        """셀 범위의 값 삭제 (인덱스 기반 시트 참조 지원)"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        worksheets = await spreadsheet.worksheets()

        # Resolve sheet reference (by name or index)
        resolved_sheet_name = self._resolve_sheet_reference(sheet_name, worksheets)
        sheet = await spreadsheet.worksheet(resolved_sheet_name)

        await sheet.batch_clear([range_str])

        return {
            "clearedRange": f"{resolved_sheet_name}!{range_str}",
        }

    @handle_api_errors
    async def add_sheet(self, spreadsheet_id: str, name: str, index: Optional[int] = None) -> dict[str, Any]:
        """새 시트 추가"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)

        # 인덱스가 지정되지 않은 경우 마지막에 추가
        if index is None:
            worksheets = await spreadsheet.worksheets()
            index = len(worksheets)

        sheet = await spreadsheet.add_worksheet(title=name, rows=1000, cols=26, index=index)

        return {
            "id": sheet.id,
            "name": sheet.title,
            "index": sheet.index,
        }

    @handle_api_errors
    async def delete_sheet(self, spreadsheet_id: str, sheet_name: str) -> None:
        """시트 삭제 (인덱스 기반 시트 참조 지원)"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        worksheets = await spreadsheet.worksheets()

        # Resolve sheet reference (by name or index)
        resolved_sheet_name = self._resolve_sheet_reference(sheet_name, worksheets)
        sheet = await spreadsheet.worksheet(resolved_sheet_name)

        await spreadsheet.del_worksheet(sheet)

    @handle_api_errors
    async def rename_sheet(self, spreadsheet_id: str, sheet_name: str, new_name: str) -> dict[str, Any] | None:
        """시트 이름 변경 (인덱스 기반 시트 참조 지원)"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        worksheets = await spreadsheet.worksheets()

        # Resolve sheet reference (by name or index)
        resolved_sheet_name = self._resolve_sheet_reference(sheet_name, worksheets)
        sheet = await spreadsheet.worksheet(resolved_sheet_name)

        # gspread-asyncio의 update_title이 NotImplemented이므로 batch_update API 사용
        # Google Sheets API의 batchUpdate 요청을 직접 구성
        update_request = {
            "requests": [
                {"updateSheetProperties": {"properties": {"sheetId": sheet.id, "title": new_name}, "fields": "title"}}
            ]
        }

        # batch_update 실행
        await spreadsheet.batch_update(update_request)

        # 업데이트된 시트 정보 반환
        return {
            "id": sheet.id,
            "name": new_name,
            "index": sheet.index,
        }

    @handle_api_errors
    async def batch_get_values(self, spreadsheet_id: str, ranges: list[str]) -> list[list[list[Any]]] | None:
        """여러 범위의 값을 한 번에 가져오기"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)

        # gspread-asyncio의 batch_get 사용
        result = await spreadsheet.batch_get(ranges)
        # Result is a list of range values
        return result

    @handle_api_errors
    async def batch_update_values(
        self, spreadsheet_id: str, updates: list[tuple[str, list[list[Any]]]]
    ) -> dict[str, Any] | None:
        """여러 범위에 값을 한 번에 업데이트"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)

        # Prepare batch update data
        batch_data = []
        total_cells = 0

        for range_name, values in updates:
            batch_data.append({"range": range_name, "values": values})
            # Count cells
            total_cells += sum(len(row) for row in values)

        # Execute batch update
        await spreadsheet.batch_update(batch_data, value_input_option="USER_ENTERED")

        return {
            "totalUpdatedCells": total_cells,
            "totalUpdatedRanges": len(updates),
            "spreadsheetId": spreadsheet_id,
        }

    @handle_api_errors
    async def batch_clear_values(self, spreadsheet_id: str, ranges: list[str]) -> dict[str, Any] | None:
        """여러 범위의 값을 한 번에 삭제"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)

        # Get all worksheets
        worksheets = await spreadsheet.worksheets()
        sheet_dict = {ws.title: ws for ws in worksheets}

        # Clear each range
        cleared_ranges = []
        for range_name in ranges:
            if "!" in range_name:
                sheet_name, cell_range = range_name.split("!", 1)
                if sheet_name in sheet_dict:
                    await sheet_dict[sheet_name].batch_clear([cell_range])
                    cleared_ranges.append(range_name)
            else:
                # If no sheet specified, use first sheet
                await worksheets[0].batch_clear([range_name])
                cleared_ranges.append(f"{worksheets[0].title}!{range_name}")

        return {"clearedRanges": cleared_ranges, "spreadsheetId": spreadsheet_id}


# 전역 클라이언트 인스턴스
_client: Optional[GoogleSheetsAsyncClient] = None


def get_async_client() -> GoogleSheetsAsyncClient:
    """Google Sheets 비동기 클라이언트 반환 (이벤트 루프 감지 포함 싱글톤)"""
    import asyncio

    global _client

    try:
        current_loop = asyncio.get_running_loop()

        # 클라이언트가 없거나 이벤트 루프가 변경된 경우 새로 생성
        if (
            _client is None
            or (hasattr(_client, "_loop") and _client._loop != current_loop)
            or (hasattr(_client, "_loop") and _client._loop.is_closed())
        ):

            if _client is not None:
                logger.debug("Recreating client due to event loop change")
            _client = GoogleSheetsAsyncClient()

    except RuntimeError:
        # 이벤트 루프가 없는 경우 (동기 컨텍스트)
        if _client is None:
            _client = GoogleSheetsAsyncClient()

    return _client

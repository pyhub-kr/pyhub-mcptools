"""Google Sheets 비동기 API 클라이언트

gspread-asyncio를 사용한 진정한 비동기 구현입니다.
- 완전한 비동기 처리
- 자동 재시도 및 rate limiting
- 객체 캐싱
- 자동 토큰 갱신
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

import gspread_asyncio
from django.conf import settings
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound

from .auth import get_credentials as get_sync_credentials
from .exceptions import AuthenticationError, GoogleSheetsError, RateLimitError, SpreadsheetNotFoundError

logger = logging.getLogger(__name__)


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
            raise AuthenticationError(f"인증 정보를 가져올 수 없습니다: {e}")

    async def _ensure_initialized(self):
        """클라이언트 매니저 초기화"""
        if not self._initialized:
            self.agcm = gspread_asyncio.AsyncioGspreadClientManager(
                self._get_credentials_func
            )
            self._initialized = True

    async def _handle_api_error(self, e: Exception):
        """API 에러 처리"""
        if isinstance(e, RefreshError):
            raise AuthenticationError("인증 토큰을 갱신할 수 없습니다. 다시 로그인하세요.")
        elif isinstance(e, SpreadsheetNotFound):
            raise SpreadsheetNotFoundError(f"요청한 리소스를 찾을 수 없습니다: {e}")
        elif isinstance(e, APIError):
            error_str = str(e)
            if "PERMISSION_DENIED" in error_str:
                raise GoogleSheetsError(f"권한이 없습니다: {e}")
            elif any(code in error_str for code in ["RESOURCE_EXHAUSTED", "429", "403"]):
                raise RateLimitError(f"API 호출 한도를 초과했습니다: {e}")
            else:
                raise GoogleSheetsError(f"Google API 오류: {e}")
        else:
            logger.error(f"예상하지 못한 오류: {type(e).__name__}: {e}")
            raise GoogleSheetsError(f"작업 중 오류가 발생했습니다: {e}")

    async def list_spreadsheets(self) -> List[Dict[str, Any]]:
        """사용자가 접근 가능한 모든 스프레드시트 목록 반환"""
        await self._ensure_initialized()

        try:
            agc = await self.agcm.authorize()
            files = await agc.list_spreadsheet_files()

            spreadsheets = []
            for file in files:
                spreadsheets.append({
                    "id": file["id"],
                    "name": file["name"],
                    "url": f"https://docs.google.com/spreadsheets/d/{file['id']}",
                    "createdTime": file.get("createdTime", ""),
                    "modifiedTime": file.get("modifiedTime", ""),
                })

            # 수정 시간 기준 내림차순 정렬
            spreadsheets.sort(key=lambda x: x["modifiedTime"], reverse=True)
            return spreadsheets

        except Exception as e:
            await self._handle_api_error(e)

    async def search_spreadsheets(
        self, search_term: str, exact_match: bool = False
    ) -> List[Dict[str, Any]]:
        """이름으로 스프레드시트 검색"""
        all_sheets = await self.list_spreadsheets()

        matches = []
        search_lower = search_term.lower()

        for sheet in all_sheets:
            sheet_name_lower = sheet["name"].lower()
            if exact_match:
                if sheet_name_lower == search_lower:
                    matches.append(sheet)
            else:
                if search_lower in sheet_name_lower:
                    matches.append(sheet)

        return matches

    async def create_spreadsheet(self, name: str) -> Dict[str, Any]:
        """새 스프레드시트 생성"""
        await self._ensure_initialized()

        try:
            agc = await self.agcm.authorize()
            spreadsheet = await agc.create(name)

            return {
                "id": spreadsheet.id,
                "name": spreadsheet.title,
                "url": spreadsheet.url,
            }
        except Exception as e:
            await self._handle_api_error(e)

    async def get_spreadsheet(self, spreadsheet_id: str):
        """스프레드시트 객체 반환"""
        await self._ensure_initialized()

        try:
            agc = await self.agcm.authorize()
            return await agc.open_by_key(spreadsheet_id)
        except Exception as e:
            await self._handle_api_error(e)

    async def get_spreadsheet_info(self, spreadsheet_id: str) -> Dict[str, Any]:
        """스프레드시트 정보 반환"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)

        sheets_info = []
        worksheets = await spreadsheet.worksheets()

        for sheet in worksheets:
            sheets_info.append({
                "id": sheet.id,
                "name": sheet.title,
                "index": sheet.index,
                "rowCount": sheet.row_count,
                "columnCount": sheet.col_count,
            })

        return {
            "id": spreadsheet.id,
            "name": spreadsheet.title,
            "url": spreadsheet.url,
            "sheets": sheets_info,
        }

    def _parse_cell_address(self, cell_str: str) -> tuple[int, int]:
        """셀 주소를 행/열 인덱스로 변환 (예: A1 -> (0, 0))"""
        match = re.match(r'^([A-Z]+)(\d+)$', cell_str)
        if not match:
            raise ValueError(f"Invalid cell address: {cell_str}")

        col_str, row_str = match.groups()
        row = int(row_str) - 1  # 0-based
        col = sum((ord(c) - ord('A') + 1) * (26 ** i)
                  for i, c in enumerate(reversed(col_str))) - 1

        return row, col

    def _trim_empty_rows_and_cols(self, values: List[List[Any]]) -> List[List[Any]]:
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
        self, all_values: List[List[Any]], start_row: int, start_col: int, mode: str
    ) -> List[List[Any]]:
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
                if (start_col >= len(all_values[row_idx]) or
                    all_values[row_idx][start_col] == ""):
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
                if (start_col >= len(all_values[row_idx]) or
                    all_values[row_idx][start_col] == ""):
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

    async def get_values(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        range_str: Optional[str] = None,
        expand_mode: Optional[str] = None
    ) -> List[List[Any]]:
        """셀 범위의 값 반환 (expand 모드 지원)"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        sheet = await spreadsheet.worksheet(sheet_name)

        try:
            if expand_mode and range_str:
                # Expand 모드일 때는 전체 데이터를 가져와서 처리
                all_values = await sheet.get_all_values()

                # 시작 셀 파싱
                if ':' in range_str:
                    range_str = range_str.split(':')[0]

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

        except Exception as e:
            await self._handle_api_error(e)

    async def set_values(
        self, spreadsheet_id: str, sheet_name: str, range_str: str, values: List[List[Any]]
    ) -> Dict[str, Any]:
        """셀 범위에 값 설정"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        sheet = await spreadsheet.worksheet(sheet_name)

        try:
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
        except Exception as e:
            await self._handle_api_error(e)

    async def clear_values(
        self, spreadsheet_id: str, sheet_name: str, range_str: str
    ) -> Dict[str, Any]:
        """셀 범위의 값 삭제"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        sheet = await spreadsheet.worksheet(sheet_name)

        try:
            await sheet.batch_clear([range_str])

            return {
                "clearedRange": f"{sheet_name}!{range_str}",
            }
        except Exception as e:
            await self._handle_api_error(e)

    async def add_sheet(
        self, spreadsheet_id: str, name: str, index: Optional[int] = None
    ) -> Dict[str, Any]:
        """새 시트 추가"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)

        try:
            # 인덱스가 지정되지 않은 경우 마지막에 추가
            if index is None:
                worksheets = await spreadsheet.worksheets()
                index = len(worksheets)

            sheet = await spreadsheet.add_worksheet(
                title=name, rows=1000, cols=26, index=index
            )

            return {
                "id": sheet.id,
                "name": sheet.title,
                "index": sheet.index,
            }
        except Exception as e:
            await self._handle_api_error(e)

    async def delete_sheet(self, spreadsheet_id: str, sheet_name: str) -> None:
        """시트 삭제"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        sheet = await spreadsheet.worksheet(sheet_name)

        try:
            await spreadsheet.del_worksheet(sheet)
        except Exception as e:
            await self._handle_api_error(e)

    async def rename_sheet(
        self, spreadsheet_id: str, sheet_name: str, new_name: str
    ) -> Dict[str, Any]:
        """시트 이름 변경"""
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        sheet = await spreadsheet.worksheet(sheet_name)

        try:
            await sheet.update_title(new_name)

            return {
                "id": sheet.id,
                "name": new_name,
                "index": sheet.index,
            }
        except Exception as e:
            await self._handle_api_error(e)


# 전역 클라이언트 인스턴스
_client: Optional[GoogleSheetsAsyncClient] = None


def get_async_client() -> GoogleSheetsAsyncClient:
    """Google Sheets 비동기 클라이언트 반환 (싱글톤)"""
    global _client
    if _client is None:
        _client = GoogleSheetsAsyncClient()
    return _client
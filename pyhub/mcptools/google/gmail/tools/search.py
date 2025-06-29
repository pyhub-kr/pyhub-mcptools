"""Gmail 검색 관련 MCP 도구"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.security import sanitize_input

from ..client_async import get_gmail_client
from ..constants import DEFAULT_MAX_RESULTS

logger = logging.getLogger(__name__)


@mcp.tool(description="Gmail 고급 이메일 검색")
async def gmail_search_messages(
    search_term: str = Field(..., description="검색어 (제목, 발신자, 수신자, 본문에서 검색)"),
    max_results: int = Field(DEFAULT_MAX_RESULTS, description="최대 조회 개수"),
    include_body: bool = Field(False, description="검색 결과에 이메일 본문 포함 여부"),
) -> str:
    """
    Gmail에서 이메일을 검색합니다.

    검색 대상:
    - 이메일 제목
    - 발신자 주소 및 이름
    - 수신자 주소 및 이름
    - 이메일 본문 내용

    검색어는 자동으로 Gmail 쿼리 형식으로 변환됩니다.
    """
    try:
        # 입력값 검증 및 정제
        search_term = sanitize_input(search_term.strip())
        if not search_term:
            raise ValueError("검색어가 필요합니다")

        max_results = max(1, min(max_results, 500))

        client = await get_gmail_client()
        result = await client.search_messages(search_term, max_results)

        # 검색 결과에 본문 포함 옵션
        if include_body and result.get("messages"):
            detailed_messages = []
            for msg in result["messages"][:5]:  # 성능을 위해 최대 5개만 상세 조회
                try:
                    detailed_msg = await client.get_message(msg["id"])
                    detailed_messages.append(detailed_msg)
                except Exception as e:
                    logger.warning(f"메시지 상세 조회 실패 (ID: {msg['id']}): {e}")
                    detailed_messages.append(msg)

            result["detailed_messages"] = detailed_messages

        result["search_term"] = search_term
        result["include_body"] = include_body

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"이메일 검색 실패: {e}")
        error_result = {
            "error": "이메일 검색 중 오류가 발생했습니다",
            "details": str(e),
            "search_term": search_term,
            "max_results": max_results,
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool(description="Gmail 발신자별 이메일 검색")
async def gmail_search_by_sender(
    sender: str = Field(..., description="발신자 이메일 주소 또는 이름"),
    max_results: int = Field(DEFAULT_MAX_RESULTS, description="최대 조회 개수"),
    days_back: Optional[int] = Field(None, description="검색 기간 (일 단위, 예: 7일 이내)"),
) -> str:
    """
    Gmail에서 특정 발신자의 이메일을 검색합니다.

    검색 옵션:
    - 이메일 주소로 정확한 검색
    - 발신자 이름으로 부분 검색
    - 기간 제한 (선택사항)
    """
    try:
        # 입력값 검증 및 정제
        sender = sanitize_input(sender.strip())
        if not sender:
            raise ValueError("발신자 정보가 필요합니다")

        max_results = max(1, min(max_results, 500))

        # Gmail 쿼리 생성
        if "@" in sender:
            # 이메일 주소로 검색
            query = f'from:"{sender}"'
        else:
            # 이름으로 검색
            query = f"from:{sender}"

        # 기간 제한 추가
        if days_back and days_back > 0:
            query += f" newer_than:{days_back}d"

        client = await get_gmail_client()
        result = await client.list_messages(query=query, max_results=max_results)

        result["sender"] = sender
        result["search_query"] = query
        result["days_back"] = days_back

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"발신자별 검색 실패: {e}")
        error_result = {
            "error": "발신자별 검색 중 오류가 발생했습니다",
            "details": str(e),
            "sender": sender,
            "max_results": max_results,
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool(description="Gmail 제목별 이메일 검색")
async def gmail_search_by_subject(
    subject: str = Field(..., description="이메일 제목 검색어"),
    exact_match: bool = Field(False, description="정확한 제목 일치 여부"),
    max_results: int = Field(DEFAULT_MAX_RESULTS, description="최대 조회 개수"),
) -> str:
    """
    Gmail에서 이메일 제목으로 검색합니다.

    검색 옵션:
    - 부분 일치: 제목에 검색어가 포함된 이메일
    - 정확한 일치: 제목이 정확히 일치하는 이메일
    """
    try:
        # 입력값 검증 및 정제
        subject = sanitize_input(subject.strip())
        if not subject:
            raise ValueError("제목 검색어가 필요합니다")

        max_results = max(1, min(max_results, 500))

        # Gmail 쿼리 생성
        if exact_match:
            query = f'subject:"{subject}"'
        else:
            query = f"subject:{subject}"

        client = await get_gmail_client()
        result = await client.list_messages(query=query, max_results=max_results)

        result["subject"] = subject
        result["exact_match"] = exact_match
        result["search_query"] = query

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"제목별 검색 실패: {e}")
        error_result = {
            "error": "제목별 검색 중 오류가 발생했습니다",
            "details": str(e),
            "subject": subject,
            "exact_match": exact_match,
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool(description="Gmail 기간별 이메일 검색")
async def gmail_search_by_date(
    days_back: int = Field(7, description="검색 기간 (일 단위, 예: 7일 이내)"),
    query_type: str = Field("all", description="검색 타입 (all, unread, starred, important)"),
    max_results: int = Field(DEFAULT_MAX_RESULTS, description="최대 조회 개수"),
) -> str:
    """
    Gmail에서 기간을 기준으로 이메일을 검색합니다.

    검색 타입:
    - all: 모든 이메일
    - unread: 읽지 않은 이메일
    - starred: 별표 표시된 이메일
    - important: 중요 이메일
    """
    try:
        # 입력값 검증
        days_back = max(1, min(days_back, 365))  # 1일 ~ 1년
        max_results = max(1, min(max_results, 500))

        # 기본 쿼리 생성
        query = f"newer_than:{days_back}d"

        # 타입별 추가 쿼리
        if query_type == "unread":
            query += " is:unread"
        elif query_type == "starred":
            query += " is:starred"
        elif query_type == "important":
            query += " is:important"

        client = await get_gmail_client()
        result = await client.list_messages(query=query, max_results=max_results)

        # 검색 정보 추가
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        result["search_period"] = {
            "days_back": days_back,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        result["query_type"] = query_type
        result["search_query"] = query

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"기간별 검색 실패: {e}")
        error_result = {
            "error": "기간별 검색 중 오류가 발생했습니다",
            "details": str(e),
            "days_back": days_back,
            "query_type": query_type,
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool(description="Gmail 첨부파일이 있는 이메일 검색")
async def gmail_search_with_attachments(
    file_type: Optional[str] = Field(None, description="파일 확장자 (예: pdf, doc, jpg)"),
    sender: Optional[str] = Field(None, description="발신자 필터"),
    days_back: Optional[int] = Field(None, description="검색 기간 (일 단위)"),
    max_results: int = Field(DEFAULT_MAX_RESULTS, description="최대 조회 개수"),
) -> str:
    """
    Gmail에서 첨부파일이 있는 이메일을 검색합니다.

    검색 옵션:
    - 특정 파일 확장자로 필터링
    - 발신자로 필터링
    - 기간으로 필터링
    """
    try:
        max_results = max(1, min(max_results, 500))

        # 기본 쿼리 (첨부파일 있음)
        query = "has:attachment"

        # 파일 타입 필터
        if file_type:
            file_type = sanitize_input(file_type.strip().lower())
            if file_type:
                query += f" filename:{file_type}"

        # 발신자 필터
        if sender:
            sender = sanitize_input(sender.strip())
            if sender:
                if "@" in sender:
                    query += f' from:"{sender}"'
                else:
                    query += f" from:{sender}"

        # 기간 필터
        if days_back and days_back > 0:
            query += f" newer_than:{days_back}d"

        client = await get_gmail_client()
        result = await client.list_messages(query=query, max_results=max_results)

        result["search_filters"] = {
            "has_attachment": True,
            "file_type": file_type,
            "sender": sender,
            "days_back": days_back,
        }
        result["search_query"] = query

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"첨부파일 검색 실패: {e}")
        error_result = {
            "error": "첨부파일 검색 중 오류가 발생했습니다",
            "details": str(e),
            "file_type": file_type,
            "sender": sender,
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

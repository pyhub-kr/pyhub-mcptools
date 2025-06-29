"""Gmail 메시지 관련 MCP 도구"""

import json
import logging
from typing import Optional

from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.security import sanitize_input
from pyhub.mcptools.core.validators import validate_email

from ..client_async import get_gmail_client
from ..constants import DEFAULT_MAX_RESULTS, MAX_RESULTS_LIMIT

logger = logging.getLogger(__name__)


@mcp.tool(description="Gmail 이메일 목록 조회")
async def gmail_list_messages(
    query: str = Field("", description="Gmail 검색 쿼리 (예: 'is:unread', 'from:example@gmail.com')"),
    max_results: int = Field(DEFAULT_MAX_RESULTS, description=f"최대 조회 개수 (1-{MAX_RESULTS_LIMIT})"),
) -> str:
    """
    Gmail 이메일 목록을 조회합니다.

    Gmail 검색 문법을 지원합니다:
    - is:unread (읽지 않은 메일)
    - is:starred (별표 표시)
    - from:someone@example.com (발신자)
    - to:someone@example.com (수신자)
    - subject:"제목" (제목 검색)
    - has:attachment (첨부파일 있음)
    - newer_than:7d (7일 이내)
    """
    try:
        # 입력값 검증 및 정제
        query = sanitize_input(query)
        max_results = max(1, min(max_results, MAX_RESULTS_LIMIT))

        client = await get_gmail_client()
        result = await client.list_messages(query=query, max_results=max_results)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"이메일 목록 조회 실패: {e}")
        error_result = {
            "error": "이메일 목록 조회 중 오류가 발생했습니다",
            "details": str(e),
            "query": query,
            "max_results": max_results,
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool(description="Gmail 특정 이메일 조회")
async def gmail_get_message(
    message_id: str = Field(..., description="이메일 메시지 ID"),
    include_body: bool = Field(True, description="이메일 본문 포함 여부"),
) -> str:
    """
    Gmail에서 특정 이메일 메시지의 상세 정보를 조회합니다.

    반환 정보:
    - 제목, 발신자, 수신자, 날짜
    - 라벨 정보
    - 이메일 본문 (텍스트/HTML)
    - 첨부파일 정보
    """
    try:
        # 입력값 검증
        message_id = sanitize_input(message_id.strip())
        if not message_id:
            raise ValueError("메시지 ID가 필요합니다")

        client = await get_gmail_client()
        message = await client.get_message(message_id)

        # 본문 제외 옵션
        if not include_body:
            message.pop("body", None)

        return json.dumps(message, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"이메일 조회 실패 (ID: {message_id}): {e}")
        error_result = {"error": "이메일 조회 중 오류가 발생했습니다", "details": str(e), "message_id": message_id}
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool(description="Gmail 이메일 발송")
async def gmail_send_message(
    to: str = Field(..., description="수신자 이메일 주소"),
    subject: str = Field(..., description="이메일 제목"),
    body: str = Field(..., description="이메일 본문"),
    body_type: str = Field("plain", description="본문 타입 (plain 또는 html)"),
    cc: Optional[str] = Field(None, description="참조 이메일 주소"),
    bcc: Optional[str] = Field(None, description="숨은 참조 이메일 주소"),
) -> str:
    """
    Gmail을 통해 이메일을 발송합니다.

    지원 기능:
    - 텍스트 및 HTML 본문
    - 참조(CC) 및 숨은 참조(BCC)
    - 자동 발신자 주소 설정
    """
    try:
        # 이메일 주소 검증
        validate_email(to)
        if cc:
            validate_email(cc)
        if bcc:
            validate_email(bcc)

        # 입력값 정제
        to = sanitize_input(to.strip())
        subject = sanitize_input(subject.strip())
        body = sanitize_input(body)
        body_type = body_type.lower() if body_type.lower() in ["plain", "html"] else "plain"

        if cc:
            cc = sanitize_input(cc.strip())
        if bcc:
            bcc = sanitize_input(bcc.strip())

        client = await get_gmail_client()
        result = await client.send_message(to=to, subject=subject, body=body, body_type=body_type, cc=cc, bcc=bcc)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")
        error_result = {"error": "이메일 발송 중 오류가 발생했습니다", "details": str(e), "to": to, "subject": subject}
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool(description="Gmail 이메일을 읽음으로 표시")
async def gmail_mark_as_read(message_id: str = Field(..., description="이메일 메시지 ID")) -> str:
    """
    Gmail에서 특정 이메일을 읽음으로 표시합니다.
    """
    try:
        # 입력값 검증
        message_id = sanitize_input(message_id.strip())
        if not message_id:
            raise ValueError("메시지 ID가 필요합니다")

        client = await get_gmail_client()
        result = await client.mark_as_read(message_id)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"읽음 표시 실패 (ID: {message_id}): {e}")
        error_result = {"error": "읽음 표시 중 오류가 발생했습니다", "details": str(e), "message_id": message_id}
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool(description="Gmail 이메일을 읽지 않음으로 표시")
async def gmail_mark_as_unread(message_id: str = Field(..., description="이메일 메시지 ID")) -> str:
    """
    Gmail에서 특정 이메일을 읽지 않음으로 표시합니다.
    """
    try:
        # 입력값 검증
        message_id = sanitize_input(message_id.strip())
        if not message_id:
            raise ValueError("메시지 ID가 필요합니다")

        client = await get_gmail_client()
        result = await client.mark_as_unread(message_id)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"읽지 않음 표시 실패 (ID: {message_id}): {e}")
        error_result = {"error": "읽지 않음 표시 중 오류가 발생했습니다", "details": str(e), "message_id": message_id}
        return json.dumps(error_result, ensure_ascii=False, indent=2)

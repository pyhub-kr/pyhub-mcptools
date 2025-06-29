"""Gmail 라벨 관련 MCP 도구"""

import json
import logging

from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.security import sanitize_input

from ..client_async import get_gmail_client

logger = logging.getLogger(__name__)


@mcp.tool(description="Gmail 라벨 목록 조회")
async def gmail_list_labels() -> str:
    """
    Gmail 계정의 모든 라벨 목록을 조회합니다.

    반환 정보:
    - 라벨 ID 및 이름
    - 라벨 타입 (시스템/사용자)
    - 메시지 수 및 읽지 않은 메시지 수
    - 라벨 표시 설정
    """
    try:
        client = await get_gmail_client()
        result = await client.list_labels()

        # 라벨 정보 정리 및 분류
        system_labels = []
        user_labels = []

        for label in result.get("labels", []):
            label_info = {
                "id": label.get("id"),
                "name": label.get("name"),
                "type": label.get("type", "user"),
                "message_list_visibility": label.get("messageListVisibility", "show"),
                "label_list_visibility": label.get("labelListVisibility", "labelShow"),
                "messages_total": label.get("messagesTotal", 0),
                "messages_unread": label.get("messagesUnread", 0),
                "threads_total": label.get("threadsTotal", 0),
                "threads_unread": label.get("threadsUnread", 0),
            }

            if label.get("type") == "system":
                system_labels.append(label_info)
            else:
                user_labels.append(label_info)

        organized_result = {
            "system_labels": system_labels,
            "user_labels": user_labels,
            "total_system_labels": len(system_labels),
            "total_user_labels": len(user_labels),
            "total_labels": len(system_labels) + len(user_labels),
        }

        return json.dumps(organized_result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"라벨 목록 조회 실패: {e}")
        error_result = {"error": "라벨 목록 조회 중 오류가 발생했습니다", "details": str(e)}
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool(description="Gmail 특정 라벨의 이메일 조회")
async def gmail_get_messages_by_label(
    label_id: str = Field(..., description="라벨 ID (예: 'INBOX', 'UNREAD', 'STARRED')"),
    max_results: int = Field(10, description="최대 조회 개수 (1-500)"),
) -> str:
    """
    Gmail에서 특정 라벨이 적용된 이메일 목록을 조회합니다.

    주요 시스템 라벨:
    - INBOX: 받은편지함
    - UNREAD: 읽지 않음
    - STARRED: 별표 표시
    - SENT: 보낸편지함
    - DRAFT: 임시보관함
    - SPAM: 스팸
    - TRASH: 휴지통
    """
    try:
        # 입력값 검증 및 정제
        label_id = sanitize_input(label_id.strip())
        if not label_id:
            raise ValueError("라벨 ID가 필요합니다")

        max_results = max(1, min(max_results, 500))

        client = await get_gmail_client()
        result = await client.list_messages(query="", max_results=max_results, label_ids=[label_id])

        # 라벨 정보 추가
        result["label_id"] = label_id
        result["filter_type"] = "label"

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"라벨별 이메일 조회 실패 (라벨: {label_id}): {e}")
        error_result = {
            "error": "라벨별 이메일 조회 중 오류가 발생했습니다",
            "details": str(e),
            "label_id": label_id,
            "max_results": max_results,
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

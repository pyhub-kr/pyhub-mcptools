"""Gmail API 비동기 클라이언트"""

import asyncio
import base64
import logging
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .auth import GmailAuth
from .constants import (
    DEFAULT_MAX_RESULTS,
    ERROR_MESSAGES,
    GMAIL_API_SERVICE_NAME,
    GMAIL_API_VERSION,
    MAX_RESULTS_LIMIT,
    MessageFormat,
)
from .exceptions import (
    GmailAPIError,
    GmailInvalidQueryError,
    GmailMessageNotFoundError,
    GmailPermissionError,
    GmailQuotaExceededError,
    GmailSendError,
)

logger = logging.getLogger(__name__)


class GmailAsyncClient:
    """Gmail API 비동기 클라이언트"""

    def __init__(self):
        self.auth = GmailAuth()
        self._service = None

    async def _get_service(self):
        """Gmail 서비스 객체 조회"""
        if self._service is None:
            credentials = self.auth.get_credentials()
            self._service = build(GMAIL_API_SERVICE_NAME, GMAIL_API_VERSION, credentials=credentials)
        return self._service

    async def _execute_request(self, request):
        """API 요청 실행 (비동기)"""
        try:
            # Google API는 동기이므로 executor로 실행
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, request.execute)
        except HttpError as e:
            await self._handle_api_error(e)
        except Exception as e:
            logger.error(f"예상하지 못한 오류: {e}")
            raise GmailAPIError(f"작업 중 오류가 발생했습니다: {e}") from e

    async def _handle_api_error(self, error: HttpError):
        """API 오류 처리"""
        status_code = error.resp.status
        error_detail = error.error_details[0] if error.error_details else {}
        # reason = error_detail.get("reason", "unknown")
        message = error_detail.get("message", str(error))

        logger.error(f"Gmail API 오류 ({status_code}): {message}")

        if status_code == 404:
            raise GmailMessageNotFoundError(ERROR_MESSAGES["message_not_found"])
        elif status_code == 403:
            if "quota" in message.lower():
                raise GmailQuotaExceededError(ERROR_MESSAGES["quota_exceeded"])
            else:
                raise GmailPermissionError(ERROR_MESSAGES["permission_denied"])
        elif status_code == 400:
            raise GmailInvalidQueryError(ERROR_MESSAGES["invalid_query"])
        else:
            raise GmailAPIError(f"Gmail API 오류: {message}")

    async def list_messages(
        self, query: str = "", max_results: int = DEFAULT_MAX_RESULTS, label_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """이메일 메시지 목록 조회 (기본 - ID만)"""
        service = await self._get_service()

        # 파라미터 검증
        if max_results > MAX_RESULTS_LIMIT:
            max_results = MAX_RESULTS_LIMIT

        try:
            request = service.users().messages().list(userId="me", q=query, maxResults=max_results, labelIds=label_ids)

            result = await self._execute_request(request)

            messages = result.get("messages", [])
            next_page_token = result.get("nextPageToken")

            return {
                "messages": messages,
                "total_count": len(messages),
                "next_page_token": next_page_token,
                "query": query,
                "max_results": max_results,
            }

        except Exception as e:
            logger.error(f"메시지 목록 조회 실패: {e}")
            raise

    async def list_messages_detailed(
        self,
        query: str = "",
        max_results: int = DEFAULT_MAX_RESULTS,
        label_ids: Optional[List[str]] = None,
        batch_size: int = 10,
    ) -> Dict[str, Any]:
        """메타데이터를 포함한 상세 메시지 목록 조회"""
        # 1단계: 기본 메시지 목록 조회
        messages_list = await self.list_messages(query, max_results, label_ids)

        if not messages_list.get("messages"):
            return messages_list

        # 2단계: 배치로 메타데이터 조회
        detailed_messages = []
        message_ids = [msg["id"] for msg in messages_list["messages"]]

        # 배치 단위로 처리
        for i in range(0, len(message_ids), batch_size):
            batch_ids = message_ids[i : i + batch_size]
            batch_messages = await self._get_messages_batch(batch_ids)
            detailed_messages.extend(batch_messages)

        return {**messages_list, "messages": detailed_messages, "include_metadata": True}

    async def _get_messages_batch(self, message_ids: List[str]) -> List[Dict[str, Any]]:
        """배치로 메시지 메타데이터 조회"""
        service = await self._get_service()
        messages = []

        # 순차 처리로 안정성 향상 (병렬 처리 시 SSL 오류 발생)
        for msg_id in message_ids:
            try:
                message = await self._get_message_metadata(service, msg_id)
                messages.append(message)
                # 각 요청 사이에 짧은 대기 시간 추가
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"메시지 메타데이터 조회 실패 (ID: {msg_id}): {e}")
                # 실패한 경우 기본 정보만 추가
                messages.append(
                    {
                        "id": msg_id,
                        "subject": "(조회 실패)",
                        "from": "Unknown",
                        "date": "",
                        "is_unread": True,  # 안전한 기본값
                        "is_starred": False,
                        "is_important": False,
                    }
                )

        return messages

    async def _get_message_metadata(self, service, message_id: str) -> Dict[str, Any]:
        """메시지 메타데이터 조회 (METADATA 형식)"""
        try:
            request = service.users().messages().get(userId="me", id=message_id, format=MessageFormat.METADATA.value)

            message = await self._execute_request(request)
            return await self._parse_message_metadata(message)

        except Exception as e:
            logger.error(f"메시지 메타데이터 조회 실패 (ID: {message_id}): {e}")
            # 실패한 경우 기본 정보만 반환
            return {
                "id": message_id,
                "subject": "(조회 실패)",
                "from": "Unknown",
                "date": "",
                "is_unread": False,
                "is_starred": False,
                "is_important": False,
            }

    async def _parse_message_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """메시지 메타데이터 파싱"""
        try:
            headers = {}
            if "payload" in message and "headers" in message["payload"]:
                for header in message["payload"]["headers"]:
                    headers[header["name"]] = header["value"]

            # 읽음 상태 확인
            label_ids = message.get("labelIds", [])
            is_unread = "UNREAD" in label_ids
            is_starred = "STARRED" in label_ids
            is_important = "IMPORTANT" in label_ids

            return {
                "id": message.get("id"),
                "thread_id": message.get("threadId"),
                "snippet": message.get("snippet", ""),
                "subject": headers.get("Subject", "(제목 없음)"),
                "from": self._parse_email_address(headers.get("From", "")),
                "to": headers.get("To", ""),
                "date": headers.get("Date", ""),
                "internal_date": message.get("internalDate"),
                "is_unread": is_unread,
                "is_starred": is_starred,
                "is_important": is_important,
                "label_ids": label_ids,
                "size_estimate": message.get("sizeEstimate", 0),
            }
        except Exception as e:
            logger.error(f"메시지 메타데이터 파싱 실패: {e}")
            return {
                "id": message.get("id", "Unknown"),
                "subject": "(파싱 실패)",
                "from": "Unknown",
                "date": "",
                "is_unread": False,
                "is_starred": False,
                "is_important": False,
            }

    def _parse_email_address(self, email_str: str) -> str:
        """이메일 주소에서 이름과 주소 파싱"""
        if not email_str:
            return "Unknown"

        try:
            if "<" in email_str and ">" in email_str:
                # "Name <email@domain.com>" 형식
                name_part = email_str.split("<")[0].strip().strip('"')
                email_part = email_str.split("<")[1].split(">")[0].strip()
                return name_part if name_part else email_part
            return email_str
        except Exception:
            return email_str

    async def get_message(self, message_id: str, format: MessageFormat = MessageFormat.FULL) -> Dict[str, Any]:
        """특정 이메일 메시지 조회"""
        service = await self._get_service()

        try:
            request = service.users().messages().get(userId="me", id=message_id, format=format.value)

            message = await self._execute_request(request)

            # 메시지 정보 파싱
            parsed_message = await self._parse_message(message)

            return parsed_message

        except Exception as e:
            logger.error(f"메시지 조회 실패 (ID: {message_id}): {e}")
            raise

    async def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """이메일 메시지 파싱"""
        try:
            headers = {}
            if "payload" in message and "headers" in message["payload"]:
                for header in message["payload"]["headers"]:
                    headers[header["name"]] = header["value"]

            # 본문 추출
            body = await self._extract_body(message.get("payload", {}))

            return {
                "id": message.get("id"),
                "thread_id": message.get("threadId"),
                "label_ids": message.get("labelIds", []),
                "snippet": message.get("snippet", ""),
                "history_id": message.get("historyId"),
                "internal_date": message.get("internalDate"),
                "size_estimate": message.get("sizeEstimate"),
                "headers": headers,
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "date": headers.get("Date", ""),
                "body": body,
            }
        except Exception as e:
            logger.error(f"메시지 파싱 실패: {e}")
            return message

    async def _extract_body(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """이메일 본문 추출"""
        body = {"text": "", "html": ""}

        try:
            if "parts" in payload:
                # 멀티파트 메시지
                for part in payload["parts"]:
                    mime_type = part.get("mimeType", "")
                    if mime_type == "text/plain":
                        body["text"] = await self._decode_body_data(part)
                    elif mime_type == "text/html":
                        body["html"] = await self._decode_body_data(part)
            else:
                # 단일 파트 메시지
                mime_type = payload.get("mimeType", "")
                if mime_type.startswith("text/"):
                    content = await self._decode_body_data(payload)
                    if mime_type == "text/html":
                        body["html"] = content
                    else:
                        body["text"] = content

        except Exception as e:
            logger.error(f"본문 추출 실패: {e}")

        return body

    async def _decode_body_data(self, part: Dict[str, Any]) -> str:
        """base64로 인코딩된 본문 데이터 디코딩"""
        try:
            body_data = part.get("body", {}).get("data", "")
            if body_data:
                # URL-safe base64 디코딩
                decoded_bytes = base64.urlsafe_b64decode(body_data + "===")
                return decoded_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"본문 디코딩 실패: {e}")

        return ""

    async def search_messages(self, search_term: str, max_results: int = DEFAULT_MAX_RESULTS) -> Dict[str, Any]:
        """이메일 검색"""
        # 검색어를 Gmail 쿼리 형식으로 변환
        query = f'subject:"{search_term}" OR from:"{search_term}" OR to:"{search_term}" OR "{search_term}"'

        return await self.list_messages(query=query, max_results=max_results)

    async def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        body_type: str = "plain",
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> Dict[str, Any]:
        """이메일 발송"""
        service = await self._get_service()

        try:
            # 이메일 생성
            if body_type == "html":
                message = MIMEText(body, "html")
            else:
                message = MIMEText(body, "plain")

            message["to"] = to
            message["subject"] = subject

            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            # 발신자 주소 설정
            from_address = self.auth.get_user_email()
            if from_address:
                message["from"] = from_address

            # base64 인코딩
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            request = service.users().messages().send(userId="me", body={"raw": raw_message})

            result = await self._execute_request(request)

            logger.info(f"이메일 발송 완료: {to}")

            return {
                "id": result.get("id"),
                "thread_id": result.get("threadId"),
                "label_ids": result.get("labelIds", []),
                "to": to,
                "subject": subject,
                "status": "sent",
            }

        except Exception as e:
            logger.error(f"이메일 발송 실패: {e}")
            raise GmailSendError(f"이메일 발송 중 오류가 발생했습니다: {e}") from e

    async def list_labels(self) -> Dict[str, Any]:
        """라벨 목록 조회"""
        service = await self._get_service()

        try:
            request = service.users().labels().list(userId="me")
            result = await self._execute_request(request)

            labels = result.get("labels", [])

            return {"labels": labels, "total_count": len(labels)}

        except Exception as e:
            logger.error(f"라벨 목록 조회 실패: {e}")
            raise

    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """메시지를 읽음으로 표시"""
        service = await self._get_service()

        try:
            request = service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]})

            result = await self._execute_request(request)

            return {"id": message_id, "status": "marked_as_read", "label_ids": result.get("labelIds", [])}

        except Exception as e:
            logger.error(f"읽음 표시 실패 (ID: {message_id}): {e}")
            raise

    async def mark_as_unread(self, message_id: str) -> Dict[str, Any]:
        """메시지를 읽지 않음으로 표시"""
        service = await self._get_service()

        try:
            request = service.users().messages().modify(userId="me", id=message_id, body={"addLabelIds": ["UNREAD"]})

            result = await self._execute_request(request)

            return {"id": message_id, "status": "marked_as_unread", "label_ids": result.get("labelIds", [])}

        except Exception as e:
            logger.error(f"읽지 않음 표시 실패 (ID: {message_id}): {e}")
            raise


# 전역 클라이언트 인스턴스
_gmail_client: Optional[GmailAsyncClient] = None


async def get_gmail_client() -> GmailAsyncClient:
    """Gmail 클라이언트 인스턴스 조회"""
    global _gmail_client
    if _gmail_client is None:
        _gmail_client = GmailAsyncClient()
    return _gmail_client

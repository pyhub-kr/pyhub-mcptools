import base64
import datetime
import logging
import os
from typing import Optional, Generator
from contextlib import contextmanager
from dataclasses import dataclass

import pythoncom
import win32com.client
from pyhub.mcptools.email.utils import html_to_text

from pyhub.mcptools.email.outlook.base import OutlookItemType, OutlookFolderType, OutlookBodyFormat
from pyhub.mcptools.email.types import Email, EmailAttachment, EmailFolderType

logger = logging.getLogger(__name__)

pythoncom.CoInitialize()


@dataclass
class OutlookFolderInfo:
    name: str
    entry_id: str


@dataclass
class OutlookConnection:
    """Outlook 연결 정보를 담는 데이터 클래스

    Attributes:
        application: Outlook 애플리케이션 객체
        outlook: Outlook MAPI 네임스페이스 객체
    """

    application: win32com.client.CDispatch
    outlook: win32com.client.CDispatch


@contextmanager
def outlook_connection() -> Generator[OutlookConnection, None, None]:
    """Outlook 애플리케이션 연결을 관리하는 context manager

    Yields:
        OutlookConnection: Outlook 연결 정보를 담은 객체

    Raises:
        AttributeError: Outlook이 설치되어 있지 않은 경우
    """
    application = win32com.client.Dispatch("Outlook.Application")
    try:
        outlook = application.GetNamespace("MAPI")
        yield OutlookConnection(application=application, outlook=outlook)
    except AttributeError:
        logger.error("Outlook이 설치되어 있지 않습니다.")
        raise


def get_folders(connection: Optional[OutlookConnection] = None) -> list[OutlookFolderInfo]:
    folders = []

    def walk_folder(_folder: win32com.client.CDispatch, level: int = 0) -> None:
        try:
            folder_name = _folder.Name
            folder_entry_id = _folder.EntryID
            folder_type = _folder.DefaultItemType
            if folder_type == OutlookItemType.olMailItem:
                folders.append(
                    OutlookFolderInfo(
                        name=folder_name,
                        entry_id=folder_entry_id,
                    )
                )
            for subfolder in _folder.Folders:
                walk_folder(subfolder, level + 1)
        except Exception as _e:
            logger.error("폴더 정보를 가져오는 중 오류 발생 : %s", _e)

    try:

        def process_folders(_conn: OutlookConnection) -> None:
            root_folder = _conn.outlook.Folders
            for folder in root_folder:
                walk_folder(folder)

        if connection is None:
            with outlook_connection() as conn:
                process_folders(conn)
        else:
            process_folders(connection)

    except AttributeError as e:
        logger.error("폴더 정보를 가져오는 중 오류 발생 : %s", e)
        return []

    return folders


def get_entry_id(
    folder_name: str,
    connection: Optional[OutlookConnection] = None,
) -> str:
    def find_entry_id(conn: OutlookConnection) -> str:
        for folder in get_folders(conn):
            if folder.name.lower() == folder_name.lower():
                return folder.entry_id
        raise ValueError(f"Folder '{folder_name}' not found.")

    if connection is None:
        with outlook_connection() as conn:
            return find_entry_id(conn)
    else:
        return find_entry_id(connection)


def get_emails(
    max_hours: int,
    query: Optional[str] = None,
    email_folder_type: Optional[EmailFolderType] = None,
    email_folder_name: Optional[str] = None,
    connection: Optional[OutlookConnection] = None,
) -> list[Email]:
    now = datetime.datetime.now()
    threshold_at = now - datetime.timedelta(hours=max_hours)

    def process_emails(_conn: OutlookConnection) -> list[Email]:
        if email_folder_type is not None:
            outlook_folder_type = OutlookFolderType.from_email_folder_type(email_folder_type)
            folder = _conn.outlook.GetDefaultFolder(outlook_folder_type)
        elif email_folder_name is not None:
            entry_id = get_entry_id(email_folder_name, _conn)
            folder = _conn.outlook.GetFolderFromID(entry_id)
        else:
            folder = _conn.outlook.GetDefaultFolder(OutlookFolderType.olFolderInbox)

        folder_items = folder.Items
        # Sort by received time, newest first
        folder_items.Sort("[ReceivedTime]", True)

        if query:
            # sql_conditions = []
            # terms = [term.strip() for term in query.split(" OR ")]
            # for term in terms:
            #     sql_conditions.append(f'"urn:schemas:httpmail:subject" LIKE "%{term}%"')
            #     sql_conditions.append(f'"urn:schemas:httpmail:fromname" LIKE "%{term}%"')
            #     sql_conditions.append(f'"urn:schemas:httpmail:textdescription" LIKE "%{term}%"')
            sql_conditions = [
                f'"urn:schemas:httpmail:subject" LIKE "%{query}%"',
            ]

            filter_term = f"@SQL=" + " OR ".join(sql_conditions)
            folder_items.Restrict(filter_term)
            logger.info("Query: %s", filter_term)

        email_list: list[Email] = []

        for message in folder_items:
            try:
                received_at = getattr(message, "ReceivedTime", None)
                if received_at:
                    # convert to naive datetime for comparison
                    received_at = received_at.replace(tzinfo=None)
                    if received_at >= threshold_at:
                        subject = getattr(message, "Subject")
                        sender_name = getattr(message, "SenderName", "")
                        sender_email = getattr(message, "SenderEmailAddress", "")
                        to = getattr(message, "To", "")
                        cc = getattr(message, "CC", "")
                        entry_id = getattr(message, "EntryID", None)
                        mail = Email(
                            identifier=entry_id,
                            subject=subject,
                            sender_name=sender_name,
                            sender_email=sender_email,
                            to=to,
                            cc=cc,
                            received_at=received_at,
                        )
                        email_list.append(mail)
            except Exception as e:
                logger.warning("메일 정보를 가져오는 중 오류 발생 : %s", e, exc_info=True)
                continue

        return email_list

    if connection is None:
        with outlook_connection() as conn:
            return process_emails(conn)
    else:
        return process_emails(connection)


def get_email(
    identifier: str,
    connection: Optional[OutlookConnection] = None,
) -> Email:
    def process_email(_conn: OutlookConnection) -> Email:
        message = _conn.outlook.GetItemFromID(identifier)
        subject = getattr(message, "Subject")
        sender_name = getattr(message, "SenderName", "")
        sender_email = getattr(message, "SenderEmailAddress", "")
        to = getattr(message, "To", "")
        cc = getattr(message, "CC", "")
        received_at = getattr(message, "ReceivedTime", None)
        if received_at:
            received_at = received_at.replace(tzinfo=None)
        plain = getattr(message, "Body", None)
        html = getattr(message, "HTMLBody", None)
        body = html_to_text(html) if html else plain or ""
        attachments: list[EmailAttachment] = []
        if hasattr(message, "Attachments") and message.Attachments.Count > 0:
            for i in range(1, message.Attachments.Count + 1):
                attachment = message.Attachments.Item(i)
                filename = attachment.FileName
                temp_path = os.path.join(os.getcwd(), filename)
                attachment.SaveAsFile(temp_path)
                with open(temp_path, "rb") as f:
                    content_base64 = base64.b64encode(f.read()).decode("utf-8")
                os.remove(temp_path)
                attachments.append(EmailAttachment(filename=filename, content_base64=content_base64))
        return Email(
            identifier=identifier,
            subject=subject,
            sender_name=sender_name,
            sender_email=sender_email,
            to=to,
            cc=cc,
            received_at=received_at,
            body=body,
            attachments=attachments,
        )

    if connection is None:
        with outlook_connection() as conn:
            return process_email(conn)
    else:
        return process_email(connection)


def get_account_for_email_address(
    smtp_address: str,
    connection: Optional[OutlookConnection] = None,
) -> win32com.client.CDispatch:
    """특정 SMTP 주소를 가진 계정을 찾아 반환합니다.

    Args:
        smtp_address (str): 찾을 SMTP 주소
        connection (Optional[OutlookConnection]): Outlook 연결 객체

    Returns:
        win32com.client.CDispatch: 찾은 계정 객체

    Raises:
        ValueError: 해당 SMTP 주소를 가진 계정이 없는 경우
    """

    def process_account(_conn: OutlookConnection) -> win32com.client.CDispatch:
        accounts = _conn.outlook.Session.Accounts
        for i in range(1, accounts.Count + 1):
            account = accounts.Item(i)
            if account.SmtpAddress == smtp_address:
                return account
        raise ValueError(f"No Account with SmtpAddress: {smtp_address} exists!")

    if connection is None:
        with outlook_connection() as conn:
            return process_account(conn)
    else:
        return process_account(connection)


def send_email(
    subject: str,
    message: str,
    from_email: str,
    recipient_list: list[str],
    html_message: Optional[str] = None,
    cc_list: Optional[list[str]] = None,
    bcc_list: Optional[list[str]] = None,
    connection: Optional[OutlookConnection] = None,
) -> None:
    """Outlook을 통해 이메일을 발송합니다.

    Args:
        subject (str): 이메일 제목
        message (str): 이메일 본문 (plain text)
        from_email (str): 발신자 이메일 주소
        recipient_list (list[str]): 수신자 이메일 주소 목록
        html_message (Optional[str], optional): HTML 형식의 이메일 본문. Defaults to None.
        cc_list (Optional[list[str]], optional): 참조 수신자 이메일 주소 목록. Defaults to None.
        bcc_list (Optional[list[str]], optional): 숨은 참조 수신자 이메일 주소 목록. Defaults to None.
        connection (Optional[OutlookConnection], optional): Outlook 연결 객체. Defaults to None.
    """

    def process_send(_conn: OutlookConnection) -> None:
        mail = _conn.application.CreateItem(OutlookItemType.olMailItem)
        mail.Subject = subject
        mail.To = "; ".join(recipient_list)

        # CC와 BCC 설정
        if cc_list:
            mail.CC = "; ".join(cc_list)
        if bcc_list:
            mail.BCC = "; ".join(bcc_list)

        # 특정 계정으로 발송 설정
        account = get_account_for_email_address(from_email, _conn)
        mail.SendUsingAccount = account

        if html_message:
            # HTML 형식으로 설정
            mail.BodyFormat = OutlookBodyFormat.olFormatHTML
            mail.HTMLBody = html_message
            mail.Body = message  # 일반 텍스트 버전도 함께 설정
        else:
            mail.BodyFormat = OutlookBodyFormat.olFormatPlain
            mail.Body = message

        # https://learn.microsoft.com/en-us/office/vba/api/outlook.mailitem.send(method)
        mail.Send()

    if connection is None:
        with outlook_connection() as conn:
            process_send(conn)
    else:
        process_send(connection)


def get_sent_mail_count(outlook: win32com.client.CDispatch) -> int:
    sent_folder = outlook.GetDefaultFolder(OutlookFolderType.olFolderSentMail)
    return sent_folder.Items.Count

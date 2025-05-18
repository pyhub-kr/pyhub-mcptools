import logging
from typing import Optional

from pyhub.mcptools.email.outlook.base import OutlookItemType, OutlookFolderType
from pyhub.mcptools.email.types import Email, EmailAttachment, EmailFolderType
from pyhub.mcptools.excel.utils import applescript_run_sync

logger = logging.getLogger(__name__)


def get_folders() -> list[dict]:
    """Outlook 폴더 목록을 가져옵니다.

    Returns:
        list[dict]: 폴더 정보 목록
    """
    script = """
    tell application "Microsoft Outlook"
        set resultStr to ""
        repeat with aFolder in mail folders
            set folderName to name of aFolder
            set resultStr to resultStr & id of aFolder & "|" & folderName & return
        end repeat
        return resultStr
    end tell
    """
    stdout_str = applescript_run_sync(script).strip()

    folders = []
    for line in stdout_str.splitlines():
        if "|" in line:
            id_, name = line.split("|", 1)
            folders.append(
                {
                    "id": id_.strip(),
                    "name": name.strip(),
                }
            )

    return folders


def get_entry_id(folder_name: str) -> str:
    """폴더 이름으로 EntryID를 조회합니다.

    Args:
        folder_name (str): 폴더 이름

    Returns:
        str: 폴더의 EntryID
    """
    for folder in get_folders():
        if folder["name"].lower() == folder_name.lower():
            return folder["id"]
    raise ValueError(f"Folder '{folder_name}' not found.")


def get_emails(
    email_folder_type: Optional[EmailFolderType] = None,
    email_folder_name: Optional[str] = None,
) -> list[Email]:
    """이메일 목록을 조회합니다.

    Args:
        email_folder_type (Optional[EmailFolderType]): 이메일 폴더 타입
        email_folder_name (Optional[str]): 이메일 폴더 이름

    Returns:
        list[Email]: 이메일 목록
    """
    # 폴더 선택
    if email_folder_type is not None:
        outlook_folder_type = OutlookFolderType.from_email_folder_type(email_folder_type)
        folder_script = f"set targetFolder to {outlook_folder_type}"
    elif email_folder_name is not None:
        entry_id = get_entry_id(email_folder_name)
        folder_script = f'set targetFolder to folder id "{entry_id}"'
    else:
        folder_script = "set targetFolder to inbox"

    # 메일 정보 조회
    script = f"""
    tell application "Microsoft Outlook"
        {folder_script}
        set messageList to messages of targetFolder
        set emailList to {{}}
        repeat with aMessage in messageList
            set emailInfo to {{subject:subject of aMessage, 
                             sender:name of sender of aMessage,
                             senderEmail:email address of sender of aMessage,
                             to:to recipients of aMessage,
                             cc:cc recipients of aMessage,
                             receivedTime:time received of aMessage,
                             body:content of aMessage,
                             hasAttachments:has attachments of aMessage}}
            set end of emailList to emailInfo
        end repeat
        return emailList
    end tell
    """

    print(script)

    stdout_str = applescript_run_sync(script)
    print(repr(stdout_str))
    print("===")

    email_list: list[Email] = []

    # if stdout_str:
    #     # AppleScript 결과를 파싱하여 Email 객체 생성
    #     # 실제 구현에서는 AppleScript 결과 파싱 로직이 필요합니다
    #     for email_data in stdout_str:
    #         attachments: list[EmailAttachment] = []
    #         if email_data.get("hasAttachments"):
    #             # 첨부파일 처리 로직 구현 필요
    #             pass

    #         mail = Email(
    #             subject=email_data.get("subject", ""),
    #             sender_name=email_data.get("sender", ""),
    #             sender_email=email_data.get("senderEmail", ""),
    #             to=email_data.get("to", ""),
    #             cc=email_data.get("cc", ""),
    #             received_at=str(email_data.get("receivedTime", "")),
    #             body=email_data.get("body", ""),
    #             attachments=attachments,
    #         )
    #         email_list.append(mail)

    return email_list

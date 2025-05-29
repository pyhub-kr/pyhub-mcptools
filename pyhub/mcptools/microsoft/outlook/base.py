from enum import IntEnum

from pyhub.mcptools.core.email_types import EmailFolderType


# https://learn.microsoft.com/en-us/office/vba/api/outlook.olbodyformat
class OutlookBodyFormat(IntEnum):
    olFormatUnspecified = 0  # Unspecified format
    olFormatPlain = 1  # Plain format
    olFormatHTML = 2  # HTML format
    olFormatRichText = 3  # Rich text format


# https://learn.microsoft.com/en-us/office/vba/api/outlook.olitemtype
class OutlookItemType(IntEnum):
    """Outlook 폴더의 기본 항목 타입을 나타내는 열거형"""

    olMailItem = 0  # 일반 폴더/메일 폴더
    olAppointmentItem = 1  # 캘린더 항목
    olContactItem = 2  # 연락처 항목
    olTaskItem = 3  # 작업 항목
    olJournalItem = 4  # 저널 항목
    olNoteItem = 5  # 메모 항목
    olPostItem = 6  # 게시 항목
    olDistributionListItem = 7


# https://learn.microsoft.com/en-us/office/vba/api/outlook.oldefaultfolders
class OutlookFolderType(IntEnum):
    # Mail related folders
    olFolderInbox = 6  # The Inbox folder
    olFolderSentMail = 5  # The Sent Mail folder
    # olFolderOutbox = 4  # The Outbox folder
    # olFolderManagedEmail = 29  # The top-level folder in the Managed Folders group (Exchange only)
    # olFolderDrafts = 16  # The Drafts folder
    # olFolderJunk = 23  # The Junk E-Mail folder
    # olFolderDeletedItems = 3  # The Deleted Items folder

    # # Calendar and Tasks
    # olFolderCalendar = 9  # The Calendar folder
    # olFolderTasks = 13  # The Tasks folder
    # olFolderToDo = 28  # The To Do folder

    # # Contacts
    # olFolderContacts = 10  # The Contacts folder
    # olFolderSuggestedContacts = 30  # The Suggested Contacts folder

    # # Notes and Journal
    # olFolderNotes = 12  # The Notes folder
    # olFolderJournal = 11  # The Journal folder

    # # RSS and Search
    # olFolderRssFeeds = 25  # The RSS Feeds folder
    # olFolderSearchFolders = 17  # The Search Folders

    # # Exchange specific folders
    # olFolderSyncIssues = 20  # The Sync Issues folder (Exchange only)
    # olFolderServerFailures = 22  # Server Failures folder (Exchange only)
    # olFolderConflicts = 19  # Conflicts folder (Exchange only)
    # olFolderLocalFailures = 21  # Local Failures folder (Exchange only)
    # olPublicFoldersAllPublicFolders = 18  # All Public Folders (Exchange only)

    @classmethod
    def from_email_folder_type(cls, folder_type: EmailFolderType) -> "OutlookFolderType":
        match folder_type:
            case EmailFolderType.INBOX:
                return cls.olFolderInbox
            case EmailFolderType.SENT:
                return cls.olFolderSentMail
            case _:
                raise ValueError(f"Invalid folder type: {folder_type}")

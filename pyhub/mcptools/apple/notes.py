"""Apple Notes integration."""

from typing import Optional, List, Dict, Any
from datetime import datetime

from pyhub.mcptools.apple.utils import (
    applescript_run,
    escape_applescript_string,
    parse_applescript_record,
)


class NotesClient:
    """Client for interacting with Apple Notes app."""

    async def list_notes(
        self,
        folder_name: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """List notes from Apple Notes.

        Args:
            folder_name: Filter by folder name (optional)
            limit: Maximum number of notes to return

        Returns:
            List of note dictionaries
        """
        folder_filter = f'of folder "{folder_name}"' if folder_name else ""

        script = f'''
        tell application "Notes"
            set outputList to {{}}
            set noteCount to 0

            repeat with theNote in notes {folder_filter}
                if noteCount ≥ {limit} then exit repeat

                set noteInfo to "ID:::" & (id of theNote as string) & "|||"
                set noteInfo to noteInfo & "Name:::" & (name of theNote as string) & "|||"
                set noteInfo to noteInfo & "Body:::" & (body of theNote as string) & "|||"
                set noteInfo to noteInfo & "CreationDate:::" & (creation date of theNote as string) & "|||"
                set noteInfo to noteInfo & "ModificationDate:::" & (modification date of theNote as string) & "|||"
                try
                    set noteInfo to noteInfo & "Folder:::" & (name of container of theNote as string)
                on error
                    set noteInfo to noteInfo & "Folder:::Notes"
                end try

                set end of outputList to noteInfo & "<<<NOTE_END>>>"
                set noteCount to noteCount + 1
            end repeat

            return my joinList(outputList, "")
        end tell

        on joinList(lst, delim)
            set AppleScript's text item delimiters to delim
            set txt to lst as text
            set AppleScript's text item delimiters to ""
            return txt
        end joinList
        '''

        result = await applescript_run(script)
        notes = []

        if result and result != "missing value":
            for note_data in result.split("<<<NOTE_END>>>"):
                if note_data.strip():
                    note_dict = parse_applescript_record(note_data.strip())
                    if note_dict:
                        notes.append(note_dict)

        return notes

    async def search_notes(
        self,
        search_text: str,
        folder_name: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search notes by text content.

        Args:
            search_text: Text to search for
            folder_name: Filter by folder name (optional)
            limit: Maximum number of notes to return

        Returns:
            List of matching note dictionaries
        """
        folder_filter = f'of folder "{folder_name}"' if folder_name else ""
        search_lower = search_text.lower()

        script = f'''
        tell application "Notes"
            set outputList to {{}}
            set noteCount to 0
            set searchText to "{escape_applescript_string(search_lower)}"

            repeat with theNote in notes {folder_filter}
                if noteCount ≥ {limit} then exit repeat

                set noteName to name of theNote as string
                set noteBody to body of theNote as string
                try
                    set nameLower to do shell script "echo " & quoted form of noteName & " | tr '[:upper:]' '[:lower:]'"
                on error
                    set nameLower to ""
                end try

                try
                    set bodyLower to do shell script "echo " & quoted form of noteBody & " | tr '[:upper:]' '[:lower:]'"
                on error
                    set bodyLower to ""
                end try

                if nameLower contains searchText or bodyLower contains searchText then
                    set noteInfo to "ID:::" & (id of theNote as string) & "|||"
                    set noteInfo to noteInfo & "Name:::" & noteName & "|||"
                    set noteInfo to noteInfo & "Body:::" & noteBody & "|||"
                    set noteInfo to noteInfo & "CreationDate:::" & (creation date of theNote as string) & "|||"
                    set noteInfo to noteInfo & "ModificationDate:::" & (modification date of theNote as string) & "|||"
                    try
                        set noteInfo to noteInfo & "Folder:::" & (name of container of theNote as string)
                    on error
                        set noteInfo to noteInfo & "Folder:::Notes"
                    end try

                    set end of outputList to noteInfo & "<<<NOTE_END>>>"
                    set noteCount to noteCount + 1
                end if
            end repeat

            return my joinList(outputList, "")
        end tell

        on joinList(lst, delim)
            set AppleScript's text item delimiters to delim
            set txt to lst as text
            set AppleScript's text item delimiters to ""
            return txt
        end joinList
        '''

        result = await applescript_run(script)
        notes = []

        if result and result != "missing value":
            for note_data in result.split("<<<NOTE_END>>>"):
                if note_data.strip():
                    note_dict = parse_applescript_record(note_data.strip())
                    if note_dict:
                        notes.append(note_dict)

        return notes

    async def create_note(
        self,
        title: str,
        body: str,
        folder_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new note.

        Args:
            title: Note title
            body: Note content
            folder_name: Folder to create note in (optional)

        Returns:
            Dictionary with creation status and note details
        """
        escaped_title = escape_applescript_string(title)
        escaped_body = escape_applescript_string(body)

        if folder_name:
            folder_ref = f'folder "{folder_name}"'
        else:
            folder_ref = 'folder "Notes"'

        script = f'''
        tell application "Notes"
            set newNote to make new note at {folder_ref} with properties {{name:"{escaped_title}", body:"{escaped_body}"}}
            return "ID:::" & (id of newNote as string) & "|||Name:::" & (name of newNote as string)
        end tell
        '''

        try:
            result = await applescript_run(script)
            note_info = parse_applescript_record(result)

            return {
                "status": "success",
                "note_id": note_info.get("ID", ""),
                "title": title,
                "body": body,
                "folder": folder_name or "default",
                "created_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific note by ID.

        Args:
            note_id: Note ID

        Returns:
            Note dictionary or None if not found
        """
        script = f'''
        tell application "Notes"
            try
                set theNote to note id "{note_id}"
                set noteInfo to "ID:::" & (id of theNote as string) & "|||"
                set noteInfo to noteInfo & "Name:::" & (name of theNote as string) & "|||"
                set noteInfo to noteInfo & "Body:::" & (body of theNote as string) & "|||"
                set noteInfo to noteInfo & "CreationDate:::" & (creation date of theNote as string) & "|||"
                set noteInfo to noteInfo & "ModificationDate:::" & (modification date of theNote as string) & "|||"
                try
                    set noteInfo to noteInfo & "Folder:::" & (name of container of theNote as string)
                on error
                    set noteInfo to noteInfo & "Folder:::Notes"
                end try
                return noteInfo
            on error
                return "NOT_FOUND"
            end try
        end tell
        '''

        result = await applescript_run(script)

        if result and result.strip() != "NOT_FOUND":
            return parse_applescript_record(result.strip())

        return None

    async def list_folders(self) -> List[str]:
        """List all folders in Notes app.

        Returns:
            List of folder names
        """
        script = '''
        tell application "Notes"
            set folderNames to {}
            repeat with theFolder in folders
                set end of folderNames to name of theFolder as string
            end repeat
            return my joinList(folderNames, "|||")
        end tell

        on joinList(lst, delim)
            set AppleScript's text item delimiters to delim
            set txt to lst as text
            set AppleScript's text item delimiters to ""
            return txt
        end joinList
        '''

        result = await applescript_run(script)

        if result and result != "missing value":
            return [f.strip() for f in result.split("|||") if f.strip()]

        return []


# Convenience functions
async def list_notes(folder_name: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """List notes from Apple Notes."""
    client = NotesClient()
    return await client.list_notes(folder_name, limit)


async def search_notes(
    search_text: str,
    folder_name: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Search notes by text content."""
    client = NotesClient()
    return await client.search_notes(search_text, folder_name, limit)


async def create_note(
    title: str,
    body: str,
    folder_name: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new note."""
    client = NotesClient()
    return await client.create_note(title, body, folder_name)


async def get_note(note_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific note by ID."""
    client = NotesClient()
    return await client.get_note(note_id)


async def list_folders() -> List[str]:
    """List all folders in Notes app."""
    client = NotesClient()
    return await client.list_folders()